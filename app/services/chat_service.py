"""
Chat service: natural language queries over the knowledge graph.
Uses cognee.recall() for graph search with Redis session memory per user.
Falls back to Postgres keyword search when Cognee has no results.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import anthropic
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.cognee_client import recall_from_graph
from app.ingest.extractor import _get_client
from app.models.rule import Rule
from app.schemas.notification import ChatSource, ChatResponse, ChatHistoryMessage, ChatHistoryResponse
from app.security.rate_limit import get_redis
from app.services.settings_service import (
    get_simple_model,
    get_litellm_base_url,
    get_anthropic_api_key,
    is_claude_enabled,
    get_llm_request_timeout,
)

logger = logging.getLogger(__name__)

_SESSION_TTL = 86400  # 24 hours

_CHAT_SYSTEM_PROMPT_BUSINESS = """\
You are a business rules assistant. Answer using only the context provided.
Explain in plain English what the rules mean for the business and its users.
Do not include code, file paths, class names, or implementation details.
If the context contains no relevant information, say clearly that no matching
rules were found and suggest using the Rules browser for a detailed search.
"""

_CHAT_SYSTEM_PROMPT_TECHNICAL = """\
You are a technical knowledge assistant. Answer using only the context provided.
Be precise: include rule names, relevant implementation detail, and code locations
when they appear in the context. If the context contains no relevant information,
say clearly that no matching rules were found and suggest using the Rules browser.
"""


def _session_key(user_id: uuid.UUID, session_id: str) -> str:
    return f"chat:{user_id}:{session_id}"


async def _load_session(user_id: uuid.UUID, session_id: str) -> list[dict]:
    r = await get_redis()
    if r is None:
        return []
    try:
        raw = await r.get(_session_key(user_id, session_id))
        return json.loads(raw) if raw else []
    except Exception as exc:
        logger.warning("Failed to load chat session: %s", exc)
        return []


async def _save_session(user_id: uuid.UUID, session_id: str, messages: list[dict]) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        await r.setex(
            _session_key(user_id, session_id),
            _SESSION_TTL,
            json.dumps(messages),
        )
    except Exception as exc:
        logger.warning("Failed to save chat session: %s", exc)


def _extract_keywords(text: str) -> list[str]:
    stop = frozenset(
        "a an the is are was were be been being have has had do does did will would could should "
        "may might shall can need to of in on at for with by from that this and or but not how "
        "what when where who which does tell me about show".split()
    )
    words = text.lower().replace("?", "").replace(".", "").split()
    return [w for w in words if w not in stop and len(w) > 2]


async def _postgres_sources(
    db: AsyncSession, keywords: list[str], limit: int = 5
) -> tuple[list[ChatSource], list[str]]:
    """Find rules matching any keyword via case-insensitive LIKE.

    Returns (sources_for_citation, context_snippets_for_llm). Both come from
    the same query so there is no extra round-trip.
    """
    if not keywords:
        return [], []

    conditions = []
    for kw in keywords[:5]:
        conditions.append(Rule.title.ilike(f"%{kw}%"))
        conditions.append(Rule.definition.ilike(f"%{kw}%"))

    q = select(Rule).where(or_(*conditions)).limit(limit)
    result = await db.execute(q)
    rules = result.scalars().all()

    sources = [ChatSource(type="rule", id=str(r.id), title=r.title) for r in rules]
    snippets = [f"Rule: {r.title}\n{r.definition}" for r in rules]
    return sources, snippets


def _fallback_answer(sources: list[ChatSource]) -> tuple[str, float]:
    """Return a graceful string when LLM is disabled or errors."""
    if sources:
        titles = ", ".join(s.title for s in sources[:3])
        return (
            f"I found these relevant rules: {titles}. "
            "The knowledge graph contains information about these topics, but I was unable to synthesise a full answer right now.",
            0.60,
        )
    return (
        "I could not find specific information about that topic in the knowledge graph. "
        "Try rephrasing your question or use the Rules browser for a detailed search.",
        0.30,
    )


async def _llm_answer(
    db: AsyncSession,
    cognee_results: list,
    sources: list[ChatSource],
    rule_snippets: list[str],
    history: list[dict],
    message: str,
    view: str,
) -> tuple[str, float]:
    """Synthesise a real LLM answer from Cognee + Postgres context."""
    # Confidence is a data-quality heuristic, not LLM self-reported certainty
    if cognee_results:
        confidence = 0.75
    elif sources:
        confidence = 0.60
    else:
        confidence = 0.40

    # Build context block: Cognee graph results + full rule title+definition snippets
    context_parts: list[str] = []
    for item in cognee_results[:5]:
        if isinstance(item, str) and len(item) > 20:
            context_parts.append(item)
        elif isinstance(item, dict):
            for key in ("text", "content", "answer", "description", "definition"):
                val = item.get(key, "")
                if isinstance(val, str) and len(val) > 20:
                    context_parts.append(val)
                    break
    context_parts.extend(rule_snippets[:5])
    context_block = "\n".join(context_parts) if context_parts else "(No matching rules found in knowledge graph)"

    system_prompt = _CHAT_SYSTEM_PROMPT_BUSINESS if view == "business" else _CHAT_SYSTEM_PROMPT_TECHNICAL

    # Check LLM enabled before making any expensive settings reads
    if not await is_claude_enabled(db):
        logger.info("Claude API disabled by admin — returning fallback chat answer")
        return _fallback_answer(sources)

    try:
        api_key = await get_anthropic_api_key(db)
        base_url = await get_litellm_base_url(db)
        model = await get_simple_model(db)
        timeout = await get_llm_request_timeout(db)
        # Commit read transaction before the potentially slow LLM call
        # (avoids idle_in_transaction_session_timeout with slow local models like Gemma)
        await db.commit()
        client = _get_client(api_key, base_url=base_url, timeout=timeout)

        # Build multi-turn conversation: history last 3 exchanges + current question with context
        conversation_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in history[-6:]
        ]
        conversation_messages.append({
            "role": "user",
            "content": f"Context from knowledge graph:\n{context_block}\n\nQuestion: {message}",
        })

        response = await client.messages.create(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=conversation_messages,
        )
        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        if not text:
            logger.warning("LLM returned empty content for chat message, using fallback")
            return _fallback_answer(sources)
        return text, confidence
    except Exception as exc:
        logger.warning("Chat LLM call failed, using fallback: %s", exc)
        return _fallback_answer(sources)


async def chat(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: str,
    message: str,
    view: str = "business",
) -> ChatResponse:
    """Send a chat message, get an AI response with sources."""
    keywords = _extract_keywords(message)

    # Load session history for context
    history = await _load_session(user_id, session_id)

    # Build context string for Cognee
    context_parts = [f"Q: {m['content']}" if m["role"] == "user" else f"A: {m['content']}"
                     for m in history[-6:]]  # last 3 exchanges
    context_query = " ".join(context_parts + [message]) if context_parts else message

    # Query Cognee knowledge graph
    cognee_results = await recall_from_graph(context_query)

    # Find Postgres sources for citation + full definition snippets for LLM context
    sources, rule_snippets = await _postgres_sources(db, keywords)

    # Add Cognee-derived sources if they look like rule IDs
    for item in cognee_results:
        if isinstance(item, dict):
            node_id = item.get("id") or item.get("node_id")
            name = item.get("name") or item.get("title") or item.get("text", "")[:60]
            if node_id and name:
                already = any(s.id == str(node_id) for s in sources)
                if not already:
                    sources.append(ChatSource(type="rule", id=str(node_id), title=name))

    answer, confidence = await _llm_answer(db, cognee_results, sources, rule_snippets, history, message, view)

    # Save updated session
    now = datetime.now(timezone.utc).isoformat()
    history.append({"role": "user", "content": message, "created_at": now})
    history.append({
        "role": "assistant",
        "content": answer,
        "confidence": confidence,
        "sources": [s.model_dump() for s in sources],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _save_session(user_id, session_id, history)

    return ChatResponse(
        message=answer,
        confidence=confidence,
        sources=sources,
        session_id=session_id,
    )


async def get_history(
    user_id: uuid.UUID,
    session_id: str,
) -> ChatHistoryResponse:
    """Retrieve chat history for a session."""
    raw = await _load_session(user_id, session_id)
    messages = []
    for m in raw:
        sources = [ChatSource(**s) for s in m.get("sources", [])]
        messages.append(ChatHistoryMessage(
            role=m["role"],
            content=m["content"],
            confidence=m.get("confidence"),
            sources=sources,
            created_at=m.get("created_at", ""),
        ))
    return ChatHistoryResponse(session_id=session_id, messages=messages)
