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

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.cognee_client import recall_from_graph
from app.models.rule import Rule
from app.schemas.notification import ChatSource, ChatResponse, ChatHistoryMessage, ChatHistoryResponse
from app.security.rate_limit import get_redis

logger = logging.getLogger(__name__)

_SESSION_TTL = 86400  # 24 hours


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


async def _postgres_sources(db: AsyncSession, keywords: list[str], limit: int = 5) -> list[ChatSource]:
    """Find rules matching any keyword via case-insensitive LIKE."""
    if not keywords:
        return []

    conditions = []
    for kw in keywords[:5]:
        conditions.append(Rule.title.ilike(f"%{kw}%"))
        conditions.append(Rule.definition.ilike(f"%{kw}%"))

    q = select(Rule).where(or_(*conditions)).limit(limit)
    result = await db.execute(q)
    rules = result.scalars().all()

    return [
        ChatSource(type="rule", id=str(r.id), title=r.title)
        for r in rules
    ]


def _format_response(cognee_results: list, sources: list[ChatSource], view: str, message: str) -> tuple[str, float]:
    """Format the LLM/Cognee answer for the requested view. Returns (text, confidence)."""
    # Try to extract text from Cognee results
    answer_parts: list[str] = []
    for item in cognee_results:
        if isinstance(item, str) and len(item) > 20:
            answer_parts.append(item)
        elif isinstance(item, dict):
            for key in ("text", "content", "answer", "description", "definition"):
                val = item.get(key, "")
                if isinstance(val, str) and len(val) > 20:
                    answer_parts.append(val)
                    break

    if answer_parts:
        raw_answer = " ".join(answer_parts[:3])
        confidence = 0.75
    elif sources:
        # Build a summary from Postgres results
        titles = ", ".join(s.title for s in sources[:3])
        raw_answer = (
            f"Based on the knowledge graph, I found relevant business rules: {titles}. "
            "These rules define the business behaviour you asked about."
        )
        confidence = 0.60
    else:
        raw_answer = (
            "I could not find specific information about that topic in the knowledge graph. "
            "Try rephrasing your question or check the Rules browser for more detail."
        )
        confidence = 0.30

    # Business view: strip any technical snippets (simple heuristic)
    if view == "business":
        lines = [ln for ln in raw_answer.splitlines() if not any(
            sig in ln for sig in ["src/", ".cs", ".py", "class ", "namespace "]
        )]
        answer = " ".join(lines) if lines else raw_answer
    else:
        answer = raw_answer

    return answer, confidence


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

    # Find Postgres sources for citation
    sources = await _postgres_sources(db, keywords)

    # Add Cognee-derived sources if they look like rule IDs
    for item in cognee_results:
        if isinstance(item, dict):
            node_id = item.get("id") or item.get("node_id")
            name = item.get("name") or item.get("title") or item.get("text", "")[:60]
            if node_id and name:
                already = any(s.id == str(node_id) for s in sources)
                if not already:
                    sources.append(ChatSource(type="rule", id=str(node_id), title=name))

    answer, confidence = _format_response(cognee_results, sources, view, message)

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
