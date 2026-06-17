"""Infer natural-language definitions for terminology entries using Claude Haiku."""
import json
import logging
import re
from typing import TYPE_CHECKING, Optional

import anthropic

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a technical glossary expert. Given a software term name and optional"
    " variants / services, write a concise 1-2 sentence definition and estimate your"
    " confidence (0.0–1.0) based only on the information provided."
    " Respond with a single JSON object — no markdown, no extra keys:\n"
    '{"definition": "...", "confidence": 0.82}'
)


async def infer_definition(
    term: str,
    variants: list[str],
    services: list[str],
    db: Optional["AsyncSession"] = None,
) -> tuple[str, float]:
    """Return (definition, confidence) for a terminology term via Haiku.

    Raises on network / parse failure — callers should catch and treat as non-fatal.
    """
    if db is not None:
        from app.services.settings_service import is_claude_enabled, get_anthropic_api_key
        if not await is_claude_enabled(db):
            raise RuntimeError("Claude API is disabled by admin")
        api_key = await get_anthropic_api_key(db)
    else:
        api_key = settings.anthropic_api_key

    variants_str = ", ".join(v for v in variants if v != term) or "none"
    services_str = ", ".join(services) or "unknown"

    user_msg = (
        f"Term: {term}\n"
        f"Variants: {variants_str}\n"
        f"Services: {services_str}"
    )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=settings.simple_model,
        max_tokens=256,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip() if response.content else "{}"
    # Strip any accidental markdown fences
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)

    payload = json.loads(text)
    definition = str(payload.get("definition", "")).strip()
    confidence = float(payload.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    if not definition:
        raise ValueError("Empty definition returned by model")

    return definition, confidence
