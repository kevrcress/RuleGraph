"""Diff router — GET /diff and GET /diff/{rule_id}."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rule import Rule, RuleVersion
from app.schemas.diff import DiffItem, PaginatedDiff, DiffDetail, DiffVersion

router = APIRouter(prefix="/diff", tags=["diff"])


@router.get("", response_model=PaginatedDiff)
async def list_diff(
    since: Optional[str] = Query(default=None, description="ISO date string, e.g. 2024-01-01"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Return paginated summary of rules changed since the given date.
    Default window: all rules if no since param.
    """
    since_dt: Optional[datetime] = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {since!r}")

    query = select(Rule)
    count_query = select(func.count()).select_from(Rule)

    if since_dt:
        query = query.where(Rule.updated_at >= since_dt)
        count_query = count_query.where(Rule.updated_at >= since_dt)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Rule.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rules = result.scalars().all()

    items = [
        DiffItem(
            rule_id=r.id,
            title=r.title,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            change_type="definition_updated",
            changed_at=r.updated_at,
        )
        for r in rules
    ]

    return PaginatedDiff(items=items, total=total, page=page, limit=limit)


@router.get("/{rule_id}", response_model=DiffDetail)
async def get_rule_diff(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return before/after diff data for a single rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    # Load version history
    versions_result = await db.execute(
        select(RuleVersion)
        .where(RuleVersion.rule_id == rule_id)
        .order_by(RuleVersion.changed_at.asc())
    )
    versions = versions_result.scalars().all()

    version_items = [
        DiffVersion(
            definition=v.definition,
            status=v.status.value if v.status and hasattr(v.status, "value") else (str(v.status) if v.status else None),
            changed_at=v.changed_at,
            change_note=v.change_note,
        )
        for v in versions
    ]

    before = version_items[-2] if len(version_items) >= 2 else None
    after = version_items[-1] if version_items else DiffVersion(
        definition=rule.definition,
        status=rule.status.value if hasattr(rule.status, "value") else str(rule.status),
        changed_at=rule.updated_at,
    )

    return DiffDetail(
        rule_id=rule.id,
        rule_title=rule.title,
        before=before,
        after=after,
        versions=version_items,
    )
