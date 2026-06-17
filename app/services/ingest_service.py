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

from app.models.ingest import IngestRun, IngestError, IngestErrorSourceEnum
from app.models.rule import Rule, RuleStatusEnum, Service, RuleService, RuleVersion

logger = logging.getLogger(__name__)

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
