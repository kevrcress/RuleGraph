"""
Admin router — ingest error monitoring.
GET /admin/ingest-errors
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ingest import IngestError
from app.schemas.ingest import IngestErrorItem, PaginatedIngestErrors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ingest-errors", response_model=PaginatedIngestErrors)
async def list_ingest_errors(
    db: AsyncSession = Depends(get_db),
):
    """Return all ingest errors for admin review."""
    count_result = await db.execute(select(func.count()).select_from(IngestError))
    total = count_result.scalar_one()

    items_result = await db.execute(
        select(IngestError).order_by(IngestError.created_at.desc())
    )
    errors = items_result.scalars().all()

    return PaginatedIngestErrors(
        items=[IngestErrorItem.model_validate(e) for e in errors],
        total=total,
    )
