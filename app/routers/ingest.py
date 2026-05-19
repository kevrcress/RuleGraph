"""
Ingest router — handles file upload and rule extraction.
POST /ingest/file
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ingest.pipeline import process_file
from app.schemas.ingest import IngestFileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/file", response_model=IngestFileResponse)
async def ingest_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a single file, extract business rules, and store them in the graph.
    Returns the number of rules extracted and the ingest run ID.
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
        source_name="file_upload",
    )

    return IngestFileResponse(
        status="success",
        rules_extracted=result.rules_extracted,
        run_id=str(result.run_id) if result.run_id else "unknown",
    )
