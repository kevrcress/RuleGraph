"""Conflicts router — GET /conflicts."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services import conflict_service
from app.schemas.conflict import ConflictOut, PaginatedConflicts

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("", response_model=PaginatedConflicts)
async def list_conflicts(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated list of detected cross-service conflicts."""
    items, total = await conflict_service.list_conflicts(db, page=page, limit=limit)
    return PaginatedConflicts(
        items=[ConflictOut.model_validate(c) for c in items],
        total=total,
        page=page,
        limit=limit,
    )
