"""Staleness-based recovery for stuck ingest runs.

A worker crash can leave a source pinned at ``ingest_status="ingesting"`` forever:
the run never completes, so nothing flips it back. This module provides the single
staleness predicate (``is_run_stale``) and the shared recovery sweep
(``reset_stale_ingests``) reused by both the worker cron (Phase 3) and the status
route (Phase 5). A run counts as stale only when it has made no progress within
``ingest_job_timeout_seconds + ingest_stale_grace_seconds`` — actively-progressing
runs are left untouched.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingest import IngestFileCheckpoint, IngestRun
from app.models.ingest_source import IngestSource
from app.services.settings_service import get_ingest_stale_threshold

logger = logging.getLogger(__name__)


def staleness_exceeded(last_progress: datetime | None, threshold_seconds: int, now: datetime) -> bool:
    """Pure staleness arithmetic: True when ``last_progress`` is older than the threshold.

    A ``None`` last_progress (no checkpoints and no started_at) counts as stale — there is
    nothing to wait for. Factored out so the cron sweep, the single-source status route, and
    the batched list lookup all share ONE definition of "too old".
    """
    if last_progress is None:
        return True
    return (now - last_progress).total_seconds() > threshold_seconds


async def is_run_stale(db: AsyncSession, run: IngestRun, threshold_seconds: int) -> bool:
    """Return True when ``run`` has made no progress within ``threshold_seconds``.

    Progress is the latest ``IngestFileCheckpoint.processed_at`` for the run if any
    checkpoints exist, else ``run.started_at`` (a fresh run with 0 files done). A
    just-started run with no checkpoints is therefore NOT stale (started_at ~ now).
    """
    last_progress = (await db.execute(
        select(IngestFileCheckpoint.processed_at)
        .where(IngestFileCheckpoint.ingest_run_id == run.id)
        .where(IngestFileCheckpoint.processed_at.is_not(None))
        .order_by(IngestFileCheckpoint.processed_at.desc())
        .limit(1)
    )).scalars().first()

    if last_progress is None:
        last_progress = run.started_at

    return staleness_exceeded(last_progress, threshold_seconds, datetime.now(timezone.utc))


async def reset_stale_ingests(db: AsyncSession) -> list[str]:
    """Flip stale ``ingesting`` sources to ``error`` and mark their runs resumable.

    Returns the list of source names that were reset. A source is reset when its
    latest run is stale, or when it has no run at all (orphaned ``ingesting``).
    Commits once at the end.
    """
    sources = (await db.execute(
        select(IngestSource).where(IngestSource.ingest_status == "ingesting")
    )).scalars().all()

    threshold = await get_ingest_stale_threshold(db)
    reset_names: list[str] = []

    for src in sources:
        # Isolate per-source failures: a transient error evaluating one source must not
        # abort the whole sweep and starve the others. The cron re-runs every 5 minutes,
        # so anything skipped here is retried on the next tick.
        try:
            run = (await db.execute(
                select(IngestRun)
                .where(IngestRun.source_name == src.name)
                .order_by(IngestRun.started_at.desc())
            )).scalars().first()

            if run is not None and not await is_run_stale(db, run, threshold):
                continue

            src.ingest_status = "error"
            src.ingest_error = "Ingest worker stopped responding (stale; auto-recovered)"
            src.ingest_progress = None
            if run is not None and run.status == "running":
                run.status = "completed_with_errors"
            reset_names.append(src.name)
        except Exception:
            logger.exception("Stale-recovery sweep failed for source %r; skipping", src.name)

    if reset_names:
        await db.commit()
        logger.warning("Auto-recovered %d stale ingest source(s): %s", len(reset_names), reset_names)

    return reset_names
