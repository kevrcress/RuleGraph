"""arq task worker — async job processing for webhook events and background tasks.

Run the worker process with:

    arq app.tasks.worker.WorkerSettings
"""
import logging

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.database import async_session_factory
from app.tasks.ingest_job import run_ingest_impl
from app.tasks.recovery import reset_stale_ingests

logger = logging.getLogger(__name__)

# Shared queue name: the worker consumes from this queue and every enqueue site
# must target it via ``_queue_name``. Without this, ``enqueue_job`` defaults to
# arq's ``arq:queue`` and jobs are never consumed by this worker.
INGEST_QUEUE_NAME = "rulegraph:tasks"


async def process_ado_webhook(ctx, payload: dict) -> None:
    """Process an ADO webhook event asynchronously."""
    event_type = payload.get("eventType", "unknown")
    resource = payload.get("resource", {})
    logger.info("Processing ADO webhook event: %s", event_type)

    if event_type == "git.push":
        repo = resource.get("repository", {}).get("name", "unknown")
        logger.info("ADO push to repo: %s — triggering ingest", repo)
        # TODO: trigger targeted ingest for the affected repo


async def run_source_ingest(ctx, source_id: str, resume: bool = False) -> None:
    """arq job: run a source ingest in the worker process.

    Delegates to the shared implementation. Job-level retry is disabled
    (``max_tries = 1``) so arq never re-runs the whole ingest; resumability is
    handled explicitly by the admin Resume endpoint, which skips already-done
    files. This keeps arq's retry from multiplying the per-file LLM retries
    (DD-001).
    """
    await run_ingest_impl(source_id, resume)


async def _sweep_stale(ctx):
    """arq cron: periodically recover stale ingests from inside the worker.

    Running the staleness sweep in the worker process means a worker crash is
    auto-recovered without any uvicorn restart. No lock is needed:
    ``reset_stale_ingests`` only touches runs older than
    ``ingest_job_timeout_seconds + ingest_stale_grace_seconds``, which exceeds
    arq's ``job_timeout`` — so arq would already have killed a job that old, and
    the sweep cannot race a still-running job.
    """
    async with async_session_factory() as db:
        names = await reset_stale_ingests(db)
        if names:
            logger.warning("Auto-recovered stale ingests: %s", names)


class WorkerSettings:
    """arq worker configuration."""
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [process_ado_webhook, run_source_ingest]
    cron_jobs = [cron(_sweep_stale, minute=set(range(0, 60, 5)))]
    queue_name = INGEST_QUEUE_NAME
    max_jobs = 10
    # Long-running clone + LLM batch ingest; allow a generous wall-clock budget.
    job_timeout = settings.ingest_job_timeout_seconds
    # Ingest is idempotent/resumable, so a single attempt is correct — never let
    # arq auto-retry the whole job (would re-do per-file LLM retries). See DD-001.
    max_tries = 1
