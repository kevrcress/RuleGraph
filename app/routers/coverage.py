"""Coverage router — GET /coverage."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services import coverage_service
from app.schemas.coverage import CoverageItem, PaginatedCoverage

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("", response_model=PaginatedCoverage)
async def list_coverage(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated list of rules with their coverage status."""
    items, total = await coverage_service.list_coverage_gaps(db, page=page, limit=limit)
    result = []
    for rule in items:
        result.append(CoverageItem(
            id=rule.id,
            title=rule.title,
            definition=rule.definition,
            coverage_status=rule.coverage_status or "uncovered",
            source_type=rule.source_type,
            created_at=rule.created_at,
        ))
    return PaginatedCoverage(
        items=result,
        total=total,
        page=page,
        limit=limit,
    )
