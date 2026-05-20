"""Terminology router — GET /terminology."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import terminology_service
from app.schemas.terminology import TerminologyOut, PaginatedTerminology

router = APIRouter(prefix="/terminology", tags=["terminology"])


@router.get("", response_model=PaginatedTerminology)
async def list_terminology(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of terminology inconsistencies across services."""
    items, total = await terminology_service.list_inconsistencies(db, page=page, limit=limit)
    return PaginatedTerminology(
        items=[TerminologyOut.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )
