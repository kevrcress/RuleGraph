"""
Rules router — paginated list and single rule retrieval.
GET /rules
GET /rules/{id}
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rule import Rule
from app.schemas.rule import RuleListItem, RuleDetail, PaginatedRules
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=PaginatedRules)
async def list_rules(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page (max 200)"),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of rules."""
    effective_limit = min(limit, settings.max_page_limit)
    offset = (page - 1) * effective_limit

    # Total count
    count_result = await db.execute(select(func.count()).select_from(Rule))
    total = count_result.scalar_one()

    # Paginated items
    items_result = await db.execute(
        select(Rule)
        .order_by(Rule.created_at.desc())
        .offset(offset)
        .limit(effective_limit)
    )
    rules = items_result.scalars().all()

    return PaginatedRules(
        items=[RuleListItem.model_validate(r) for r in rules],
        total=total,
        page=page,
        limit=effective_limit,
    )


@router.get("/{rule_id}", response_model=RuleDetail)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the full detail for a single rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    return RuleDetail.model_validate(rule)
