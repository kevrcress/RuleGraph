"""Helpers for reading system settings from the DB at runtime."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import SystemSetting

# Sentinel stored in DB to distinguish "key is set" from the actual value.
_MASKED = "***SET***"


async def get_system_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting is not None else default


async def is_claude_enabled(db: AsyncSession) -> bool:
    """Return False only when admin has explicitly set claude_enabled=false."""
    value = await get_system_setting(db, "claude_enabled", "true")
    return value.lower() not in ("false", "0", "no", "off")


async def get_complexity_threshold(db: AsyncSession) -> float:
    """Return the complexity threshold from DB, falling back to config default."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "complexity_threshold", "")
    if not value:
        return _settings.complexity_threshold
    try:
        return max(0.0, min(1.0, float(value)))
    except ValueError:
        return _settings.complexity_threshold


async def get_llm_request_timeout(db: AsyncSession) -> int:
    """Return the LLM request timeout in seconds: DB first, config default fallback."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "llm_request_timeout_seconds", "")
    if not value:
        return _settings.llm_request_timeout_seconds
    try:
        return int(value)
    except ValueError:
        return _settings.llm_request_timeout_seconds


async def get_ingest_stale_grace(db: AsyncSession) -> int:
    """Return the ingest stale-grace seconds: DB first, config default fallback."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "ingest_stale_grace_seconds", "")
    if not value:
        return _settings.ingest_stale_grace_seconds
    try:
        return int(value)
    except ValueError:
        return _settings.ingest_stale_grace_seconds


async def get_ingest_stale_threshold(db: AsyncSession) -> int:
    """Seconds of no-progress before a run is declared dead: job timeout + grace.

    Single source of truth for the staleness threshold, shared by the recovery sweep
    (``app/tasks/recovery.py``) and the status route (``_latest_run_progress``) so the
    two can never disagree on how long is "too long".
    """
    from app.config import settings as _settings
    return _settings.ingest_job_timeout_seconds + await get_ingest_stale_grace(db)


async def get_litellm_base_url(db: AsyncSession) -> str:
    """Return the LiteLLM proxy base URL: DB first, env var fallback."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "litellm_base_url", "")
    return value or _settings.litellm_base_url


async def get_simple_model(db: AsyncSession) -> str:
    """Return the simple/fast LLM model name: DB first, config fallback."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "simple_model", "")
    return value or _settings.simple_model


async def get_complex_model(db: AsyncSession) -> str:
    """Return the complex/capable LLM model name: DB first, config fallback."""
    from app.config import settings as _settings
    value = await get_system_setting(db, "complex_model", "")
    return value or _settings.complex_model


async def get_anthropic_api_key(db: AsyncSession) -> str:
    """Return the Anthropic API key: DB (encrypted) first, env var fallback.

    Raises RuntimeError if neither source has a value.
    """
    from app.config import settings as _settings
    from app.security.encryption import decrypt_secret

    raw = await get_system_setting(db, "anthropic_api_key", "")
    if raw and raw != _MASKED:
        try:
            return decrypt_secret(raw)
        except Exception:
            pass  # corrupt/old value — fall through to env

    if _settings.anthropic_api_key:
        return _settings.anthropic_api_key

    raise RuntimeError(
        "Anthropic API key not configured. Set it in Admin → Settings or via ANTHROPIC_API_KEY env var."
    )
