"""
Ingest service — retry logic, error logging, and run tracking.
Manages IngestRun and IngestError records in Postgres.
"""
import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingest import IngestRun, IngestError, IngestErrorSourceEnum
from app.models.rule import Rule, RuleStatusEnum

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


async def store_rule(
    db: AsyncSession,
    title: str,
    definition: str,
    confidence: float,
    source_type: str,
    cognee_node_id: Optional[str] = None,
) -> Rule:
    """Write an extracted rule to the rules table."""
    rule = Rule(
        id=uuid.uuid4(),
        title=title,
        definition=definition,
        status=RuleStatusEnum.proposed,
        extraction_confidence=confidence,
        source_type=source_type,
        cognee_node_id=cognee_node_id,
    )
    db.add(rule)
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
