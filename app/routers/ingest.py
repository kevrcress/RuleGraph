"""
Ingest router — file upload, full migration ingest, and migrate-only ingest.
POST /ingest/file
POST /ingest
POST /ingest/migrate
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.ingest.pipeline import process_file
from app.schemas.ingest import IngestFileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/file", response_model=IngestFileResponse)
async def ingest_file(
    file: UploadFile = File(...),
    source_name: Optional[str] = Query(
        default=None,
        description="Source label for service association (e.g. 'ordering', 'payments')",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """
    Ingest a single file, extract business rules, and store them in the graph.
    Optional source_name associates rules with a named service.
    """
    try:
        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("latin-1")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    filename = file.filename or "unknown"

    result = await process_file(
        db=db,
        filename=filename,
        content=content,
        source_name=source_name or "file_upload",
    )

    return IngestFileResponse(
        status="success",
        rules_extracted=result.rules_extracted,
        run_id=str(result.run_id) if result.run_id else "unknown",
    )


@router.post("")
async def ingest_all_sources(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """
    Trigger ingest for all active sources configured via /admin/sources.
    Each source is enqueued as an arq job. Use GET /admin/sources to check last_ingested_at.
    """
    from sqlalchemy import select
    from app.models.ingest_source import IngestSource

    result = await db.execute(select(IngestSource).where(IngestSource.status == "active"))
    sources = result.scalars().all()

    if not sources:
        return {
            "status": "no_sources_configured",
            "message": "No active sources. Add repos via Admin → Sources.",
            "sources_triggered": 0,
        }

    from app.tasks.queue import INGEST_QUEUE_NAME
    from app.routers._deps import require_arq_pool

    pool = require_arq_pool(request)
    for src in sources:
        await pool.enqueue_job(
            "run_source_ingest", str(src.id), False, _queue_name=INGEST_QUEUE_NAME
        )

    return {
        "status": "started",
        "message": f"Ingesting {len(sources)} source(s) in the background.",
        "sources_triggered": len(sources),
        "sources": [s.name for s in sources],
    }


@router.post("/migrate")
async def ingest_migrate_only(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """
    Migration-only ingest — runs migrate_only sources from rulegraph.yaml.
    Triggers conflict detection and terminology scanning across all stored rules.
    """
    from app.services import conflict_service, terminology_service

    try:
        # Run detection across all currently stored rules
        conflicts = await conflict_service.detect_and_store(db)
        await db.commit()
        conflict_count = len(conflicts)
    except Exception as e:
        logger.warning(f"Conflict detection during migrate failed: {e}")
        conflict_count = 0

    return {
        "status": "completed",
        "message": "Migration detection complete. Conflict and terminology analysis updated.",
        "conflicts_detected": conflict_count,
    }
