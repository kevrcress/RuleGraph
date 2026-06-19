"""
Ingest service — retry logic, error logging, run tracking, service management.
Manages IngestRun, IngestError, Service, and RuleService records in Postgres.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingest import IngestRun, IngestError, IngestErrorSourceEnum, IngestFileCheckpoint
from app.models.ingest_source import IngestSource
from app.models.rule import Rule, RuleStatusEnum, Service, RuleService, RuleVersion

logger = logging.getLogger(__name__)


async def latest_run_for_source(db: AsyncSession, source_name: str) -> Optional[IngestRun]:
    """Return a source's most recent IngestRun, or None.

    Linkage is by ``source_name`` (ingest_runs has no source FK). "Latest" is
    ``started_at DESC, id DESC`` — the ``id`` tiebreaker makes the result deterministic
    when two runs share a started_at. Single source of truth for the recovery sweep, the
    resume gate, and (matching the ordering) the batched list lookup. See IV-016.
    """
    return (await db.execute(
        select(IngestRun)
        .where(IngestRun.source_name == source_name)
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .limit(1)
    )).scalars().first()


def is_run_resumable(run_status: Optional[str], src_ingest_status: str) -> bool:
    """Whether a run is incomplete enough to resume.

    A run is "incomplete" when its status is still ``running``/``completed_with_errors``,
    or when the source itself is in an ``error``/``ingesting`` state. Shared by the
    server-side resume gate (``find_resumable_run``) and the status route's ``can_resume``
    flag so the UI's enable-state and the server's accept/reject can never drift apart.
    """
    if run_status is None:
        return False
    return run_status in ("running", "completed_with_errors") or src_ingest_status in ("error", "ingesting")


async def find_resumable_run(db: AsyncSession, src: IngestSource) -> Optional[IngestRun]:
    """Return the source's latest IngestRun if it is resumable, else None."""
    run = await latest_run_for_source(db, src.name)
    if run is None:
        return None
    if is_run_resumable(run.status, src.ingest_status):
        return run
    return None

# Retry configuration per error source
RETRY_CONFIG = {
    "llm_extraction":   {"max_retries": 1, "backoff_seconds": 2},
    "cognee_ingest":    {"max_retries": 1, "backoff_seconds": 2},
    "source_connector": {"max_retries": 2, "backoff_seconds": 5},
    "document_parse":   {"max_retries": 0},
}


async def start_run(db: AsyncSession, source_name: str) -> IngestRun:
    """Create a new ingest_runs record and return it."""
    run = IngestRun(
        id=uuid.uuid4(),
        source_name=source_name,
        status="running",
        files_processed=0,
        files_errored=0,
    )
    db.add(run)
    await db.flush()
    return run


async def complete_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    files_processed: int,
    files_errored: int,
    last_processed_file: Optional[str] = None,
) -> None:
    """Update an existing ingest run to completed/failed state."""
    result = await db.execute(select(IngestRun).where(IngestRun.id == run_id))
    run = result.scalar_one_or_none()
    if run:
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        run.files_processed = files_processed
        run.files_errored = files_errored
        if last_processed_file:
            run.last_processed_file = last_processed_file
        await db.flush()


async def mark_file_checkpoint(
    db: AsyncSession,
    run_id: uuid.UUID,
    file_path: str,
    status: str,
    error_message: Optional[str] = None,
) -> IngestFileCheckpoint:
    """Upsert a per-file checkpoint for an ingest run.

    Keyed on (ingest_run_id, file_path). Sets processed_at=now() when status
    is "done" or "error". Follows the select-then-insert/update pattern of store_rule.
    """
    result = await db.execute(
        select(IngestFileCheckpoint)
        .where(IngestFileCheckpoint.ingest_run_id == run_id)
        .where(IngestFileCheckpoint.file_path == file_path)
    )
    checkpoint = result.scalar_one_or_none()

    processed_at = datetime.now(timezone.utc) if status in ("done", "error") else None

    if checkpoint is not None:
        checkpoint.status = status
        checkpoint.error_message = error_message
        checkpoint.processed_at = processed_at
        await db.flush()
        return checkpoint

    checkpoint = IngestFileCheckpoint(
        id=uuid.uuid4(),
        ingest_run_id=run_id,
        file_path=file_path,
        status=status,
        error_message=error_message,
        processed_at=processed_at,
    )
    db.add(checkpoint)
    await db.flush()
    return checkpoint


async def get_done_files(db: AsyncSession, run_id: uuid.UUID) -> set[str]:
    """Return the set of file paths already marked done for an ingest run."""
    result = await db.execute(
        select(IngestFileCheckpoint.file_path)
        .where(IngestFileCheckpoint.ingest_run_id == run_id)
        .where(IngestFileCheckpoint.status == "done")
    )
    return set(result.scalars().all())


async def count_checkpoint_tallies(db: AsyncSession, run_id: uuid.UUID) -> tuple[int, int]:
    """Return ``(done_count, error_count)`` from a run's checkpoints in one query.

    The persisted ``IngestRun.files_processed``/``files_errored`` are derived from this
    so a run completed across a crash + resume reports the cross-attempt totals, not just
    the final pass's local counters (the resume pass starts both counters at 0). Used by
    both the normal completion path and ``_finalize_empty_resume``. See DEC-045 / IV-001.
    """
    from sqlalchemy import func

    rows = (await db.execute(
        select(IngestFileCheckpoint.status, func.count())
        .where(IngestFileCheckpoint.ingest_run_id == run_id)
        .group_by(IngestFileCheckpoint.status)
    )).all()
    by_status = {status: count for status, count in rows}
    return by_status.get("done", 0), by_status.get("error", 0)


async def log_error(
    db: AsyncSession,
    run_id: Optional[uuid.UUID],
    source_name: Optional[str],
    file_path: Optional[str],
    error_source: str,
    error_message: str,
    raw_content: Optional[str] = None,
    stack_trace: Optional[str] = None,
) -> None:
    """Write an error record to the ingest_errors table."""
    try:
        source_enum = IngestErrorSourceEnum(error_source)
    except ValueError:
        source_enum = None

    error = IngestError(
        id=uuid.uuid4(),
        ingest_run_id=run_id,
        source_name=source_name,
        file_path=file_path,
        error_source=source_enum,
        error_message=error_message,
        raw_content=raw_content,
        stack_trace=stack_trace,
    )
    db.add(error)
    await db.flush()


async def get_or_create_service(db: AsyncSession, service_name: str) -> Service:
    """Get an existing Service by name or create a new one."""
    result = await db.execute(select(Service).where(Service.name == service_name))
    service = result.scalar_one_or_none()
    if service is None:
        service = Service(
            id=uuid.uuid4(),
            name=service_name,
            source_name=service_name,
        )
        db.add(service)
        await db.flush()
    return service


async def store_rule(
    db: AsyncSession,
    title: str,
    definition: str,
    confidence: float,
    source_type: str,
    cognee_node_id: Optional[str] = None,
    service_id: Optional[uuid.UUID] = None,
    source_file: Optional[str] = None,
) -> Rule:
    """Upsert a rule by (title, service_id) — update if already ingested, insert if new."""
    existing: Optional[Rule] = None

    if service_id is not None:
        result = await db.execute(
            select(Rule)
            .join(RuleService, RuleService.rule_id == Rule.id)
            .where(RuleService.service_id == service_id)
            .where(Rule.title == title)
        )
        existing = result.scalar_one_or_none()

    if existing is not None:
        existing.code_behavior = definition
        if existing.definition != definition:
            # Snapshot the current policy before recording drift
            version = RuleVersion(
                id=uuid.uuid4(),
                rule_id=existing.id,
                definition=existing.definition,
                status=existing.status,
                changed_at=datetime.now(timezone.utc),
                change_note="auto: code re-ingested, drift detected",
            )
            db.add(version)
            existing.status = RuleStatusEnum.drift
        existing.extraction_confidence = confidence
        existing.cognee_node_id = cognee_node_id
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    rule = Rule(
        id=uuid.uuid4(),
        title=title,
        definition=definition,
        code_behavior=definition,
        status=RuleStatusEnum.proposed,
        extraction_confidence=confidence,
        source_type=source_type,
        source_file=source_file,
        cognee_node_id=cognee_node_id,
        coverage_status="uncovered",
    )
    db.add(rule)
    await db.flush()

    if service_id is not None:
        db.add(RuleService(rule_id=rule.id, service_id=service_id))
        await db.flush()

    return rule


async def with_retry(
    operation_name: str,
    coro_factory,
) -> tuple[any, Optional[Exception]]:
    """
    Execute an async operation with retry logic per RETRY_CONFIG.

    Args:
        operation_name: Key in RETRY_CONFIG (e.g. "llm_extraction")
        coro_factory: Callable that returns a new coroutine each call.

    Returns:
        (result, None) on success, (None, exception) on final failure.
    """
    config = RETRY_CONFIG.get(operation_name, {"max_retries": 0})
    max_retries = config.get("max_retries", 0)
    backoff = config.get("backoff_seconds", 0)

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            result = await coro_factory()
            return result, None
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"{operation_name} attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {backoff}s..."
                )
                if backoff > 0:
                    await asyncio.sleep(backoff)
            else:
                logger.error(
                    f"{operation_name} failed after {attempt + 1} attempt(s): {e}"
                )

    return None, last_exception
