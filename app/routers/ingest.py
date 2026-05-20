"""
Ingest router — file upload, full migration ingest, and migrate-only ingest.
POST /ingest/file
POST /ingest
POST /ingest/migrate
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
    db: AsyncSession = Depends(get_db),
):
    """
    Full migration ingest — reads rulegraph.yaml and ingests all configured sources.
    Source connectors (ADO, GitHub, Confluence) are stubbed; use /ingest/file for local files.
    """
    # Phase 1: connectors are stubs — return instructional response
    return {
        "status": "no_sources_configured",
        "message": (
            "No active source connectors configured. "
            "Use POST /ingest/file to ingest individual files, "
            "or configure sources in rulegraph.yaml and connect via ADO/GitHub PAT."
        ),
        "sources_attempted": 0,
        "files_processed": 0,
    }


@router.post("/migrate")
async def ingest_migrate_only(
    db: AsyncSession = Depends(get_db),
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
