"""
Auto-generates wiki pages from extracted rules, grouped by service module.
Called at the end of batch ingest. Best-effort — failures are logged but
do not affect the ingest result.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.extractor import _get_client, _ensure_legacy_client
from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a technical documentation writer for a software engineering team.
You will be given a list of business rules extracted from a software module.
Write a clear, well-structured wiki page that documents what this module does
and the key business rules that govern it.

Write for a mixed audience — business stakeholders and developers.
Use plain English. Use markdown formatting (headers, bullet lists, bold for
key terms). Do not invent rules that are not in the list provided.
Keep it concise and factual."""


def _module_title(module: str) -> str:
    """Turn 'PaymentsService/billing' into 'Billing — PaymentsService'."""
    parts = module.split("/", 1)
    if len(parts) == 1:
        return parts[0]
    repo, mod = parts
    return f"{mod.replace('_', ' ').replace('-', ' ').title()} — {repo}"


@dataclass
class RuleSummary:
    id: str
    title: str
    definition: str


async def generate_wiki_page(
    module: str,
    rules: list[RuleSummary],
    module_summary: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[str]:
    """
    Call the LLM to synthesize a wiki page for a module from its rules.
    module_summary is the aggregated code-level description from ingest.
    Returns the markdown content string, or None on failure.
    """
    if not rules and not module_summary:
        return None

    if db is not None:
        from app.services.settings_service import is_claude_enabled, get_anthropic_api_key
        if not await is_claude_enabled(db):
            logger.info("Claude disabled — skipping wiki generation for '%s'", module)
            return None
        client = _get_client(await get_anthropic_api_key(db))
    else:
        client = _ensure_legacy_client()

    parts = [f"Module: {module}\n"]
    if module_summary:
        parts.append(f"What this module does:\n{module_summary}\n")
    if rules:
        rule_lines = "\n".join(f"- **{r.title}**: {r.definition}" for r in rules)
        parts.append(f"Extracted business rules ({len(rules)} total):\n{rule_lines}\n")
    parts.append("Write a wiki page for this module.")
    user_content = "\n".join(parts)

    try:
        response = await client.messages.create(
            model=settings.complex_model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text if response.content else None
    except Exception as exc:
        logger.warning("Wiki generation failed for '%s' (non-fatal): %s", module, exc)
        return None


async def upsert_wiki_page(
    db: AsyncSession,
    module: str,
    content: str,
    rule_ids: list[str],
) -> None:
    """Insert or update the wiki_pages row for a module."""
    from app.models.wiki import WikiPage

    result = await db.execute(select(WikiPage).where(WikiPage.module == module))
    page = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    title = _module_title(module)

    if page is None:
        page = WikiPage(
            id=uuid.uuid4(),
            module=module,
            title=title,
            content=content,
            linked_rule_ids=rule_ids,
            last_generated_at=now,
        )
        db.add(page)
    else:
        page.title = title
        page.content = content
        page.linked_rule_ids = rule_ids
        page.last_generated_at = now
        page.updated_at = now

    await db.flush()


async def generate_wiki_for_modules(
    db: AsyncSession,
    module_rules: dict[str, list[RuleSummary]],
    module_summaries: Optional[dict[str, str]] = None,
) -> dict[str, int]:
    """
    Generate and upsert wiki pages for all modules in module_rules.
    module_summaries maps module name → aggregated code description from ingest.
    Returns a summary dict {module: rule_count} for pages that were written.
    """
    written: dict[str, int] = {}
    for module, rules in module_rules.items():
        summary = (module_summaries or {}).get(module)
        content = await generate_wiki_page(module, rules, module_summary=summary, db=db)
        if content:
            await upsert_wiki_page(
                db,
                module=module,
                content=content,
                rule_ids=[r.id for r in rules],
            )
            written[module] = len(rules)
            logger.info("Wiki page generated for module '%s' (%d rules)", module, len(rules))
        else:
            logger.info("Wiki generation skipped for module '%s'", module)
    return written
