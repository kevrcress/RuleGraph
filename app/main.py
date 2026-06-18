"""
RuleGraph FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.routers import ingest, rules, admin, auth, webhooks
from app.routers import documents, conflicts, coverage, terminology, diff
from app.routers import chat, subscriptions, notifications
from app.routers import feedback, wiki, graph, sources
from app.config import settings
from app.graph.cognee_client import init_cognee, ingest_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title="RuleGraph", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    import asyncio
    from app.database import async_session_factory
    async with async_session_factory() as _db:
        await init_cognee(_db)
    asyncio.create_task(ingest_skills())
    try:
        from arq.connections import RedisSettings, create_pool
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Could not create arq pool on startup", exc_info=True)
        app.state.arq_pool = None
    try:
        await _reset_stuck_ingests()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Could not reset stuck ingests on startup", exc_info=True)
    try:
        await _seed_default_settings()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Could not seed default settings on startup", exc_info=True)


@app.on_event("shutdown")
async def shutdown():
    pool = getattr(app.state, "arq_pool", None)
    if pool is not None:
        await pool.aclose()


async def _seed_default_settings() -> None:
    """Ensure factory-default system settings exist without overwriting admin changes."""
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.settings import SystemSetting

    defaults = {"complexity_threshold": "0.5"}
    async with async_session_factory() as db:
        for key, value in defaults.items():
            result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
            if result.scalar_one_or_none() is None:
                db.add(SystemSetting(key=key, value=value))
        await db.commit()


async def _reset_stuck_ingests() -> None:
    """Recover stale 'ingesting' sources at web startup, staleness-aware.

    Delegates to ``reset_stale_ingests``, which only resets sources whose latest
    run has made no progress within ``job_timeout + grace``. A uvicorn restart
    while a worker is still legitimately ingesting therefore no longer false-flips
    a healthy in-flight run to ``error``.
    """
    import logging
    from app.database import async_session_factory
    from app.tasks.recovery import reset_stale_ingests

    logger = logging.getLogger(__name__)
    async with async_session_factory() as db:
        names = await reset_stale_ingests(db)
        if names:
            logger.warning(f"Reset stale ingests on startup: {names}")


# Public endpoints (no JWT required)
app.include_router(auth.router)
app.include_router(webhooks.router)

# Protected endpoints (JWT required per route dependency)
app.include_router(ingest.router)
app.include_router(rules.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(conflicts.router)
app.include_router(coverage.router)
app.include_router(terminology.router)
app.include_router(diff.router)
app.include_router(chat.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)
app.include_router(feedback.router)
app.include_router(wiki.router)
app.include_router(graph.router)
app.include_router(sources.router)
