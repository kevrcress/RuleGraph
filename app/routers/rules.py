"""
Rules router — browse, create, update, and lineage.
All endpoints require JWT auth.
"""
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.rule import Rule
from app.schemas.rule import (
    PaginatedRules,
    RuleCreate,
    RuleCreateResponse,
    RuleDetail,
    RuleListItem,
    RuleUpdate,
    LineageResponse,
    LineageEvent,
)
from app.services import rule_service, notification_service, impact_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=PaginatedRules)
async def list_rules(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    effective_limit = min(limit, settings.max_page_limit)
    offset = (page - 1) * effective_limit

    count_result = await db.execute(select(func.count()).select_from(Rule))
    total = count_result.scalar_one()

    items_result = await db.execute(
        select(Rule).order_by(Rule.created_at.desc()).offset(offset).limit(effective_limit)
    )
    rules = items_result.scalars().all()

    return PaginatedRules(
        items=[RuleListItem.model_validate(r) for r in rules],
        total=total,
        page=page,
        limit=effective_limit,
    )


@router.post("", response_model=RuleCreateResponse, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    owner_id = uuid.UUID(current_user["sub"])
    rule, assists = await rule_service.propose_rule(
        db=db,
        title=body.title,
        definition=body.definition,
        owner_id=owner_id,
        source_type=body.source_type or "chat",
    )
    return RuleCreateResponse(
        id=rule.id,
        title=rule.title,
        definition=rule.definition,
        status=rule.status,
        owner_id=rule.owner_id,
        created_at=rule.created_at,
        authoring_assists=assists,
    )


@router.get("/{rule_id}", response_model=RuleDetail)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return RuleDetail.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleDetail)
async def update_rule(
    rule_id: uuid.UUID,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    updater_id = uuid.UUID(current_user["sub"])
    try:
        rule = await rule_service.update_rule(
            db=db,
            rule_id=rule_id,
            updater_id=updater_id,
            title=body.title,
            definition=body.definition,
            status=body.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Fire notifications if status changed
    if body.status is not None:
        await notification_service.notify_rule_status_change(
            db=db,
            rule_id=rule_id,
            new_status=body.status.value if hasattr(body.status, "value") else str(body.status),
            actor_id=updater_id,
        )
        await db.commit()

    return RuleDetail.model_validate(rule)


@router.get("/{rule_id}/impact")
async def get_impact(
    rule_id: uuid.UUID,
    view: str = Query(default="technical"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return await impact_service.get_impact(db, rule_id, view=view)


@router.get("/{rule_id}/impact/reverse")
async def get_reverse_impact(
    rule_id: uuid.UUID,
    view: str = Query(default="technical"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return await impact_service.get_reverse_impact(db, rule_id, view=view)


@router.get("/{rule_id}/lineage", response_model=LineageResponse)
async def get_lineage(
    rule_id: uuid.UUID,
    since: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    events = await rule_service.get_lineage(db, rule_id, since=since)
    return LineageResponse(
        rule_id=rule_id,
        events=[LineageEvent.model_validate(e) for e in events],
    )
