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
        await _reset_stuck_ingests()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Could not reset stuck ingests on startup", exc_info=True)
    try:
        await _seed_default_settings()
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Could not seed default settings on startup", exc_info=True)


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
    """Any source still marked 'ingesting' at startup had its task killed mid-run."""
    import logging
    from sqlalchemy import update
    from app.database import async_session_factory
    from app.models.ingest_source import IngestSource

    logger = logging.getLogger(__name__)
    async with async_session_factory() as db:
        result = await db.execute(
            update(IngestSource)
            .where(IngestSource.ingest_status == "ingesting")
            .values(ingest_status="error", ingest_error="Ingest was interrupted (server restarted)")
            .returning(IngestSource.name)
        )
        names = [row[0] for row in result.fetchall()]
        if names:
            await db.commit()
            logger.warning(f"Reset stuck ingests on startup: {names}")


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
