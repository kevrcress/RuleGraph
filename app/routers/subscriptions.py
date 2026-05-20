"""
Subscriptions router — GET/POST /subscriptions, DELETE /subscriptions/{id}.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Subscription
from app.schemas.notification import SubscriptionCreate, SubscriptionResponse, PaginatedSubscriptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=PaginatedSubscriptions)
async def list_subscriptions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    offset = (page - 1) * limit

    total = (await db.execute(
        select(func.count()).select_from(Subscription).where(Subscription.user_id == user_id)
    )).scalar_one()

    items = (await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .offset(offset)
        .limit(limit)
    )).scalars().all()

    return PaginatedSubscriptions(
        items=[SubscriptionResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])

    # Idempotent: return existing if already subscribed
    existing = (await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.target_type == body.target_type,
            Subscription.target_id == body.target_id,
        )
    )).scalar_one_or_none()

    if existing:
        return SubscriptionResponse.model_validate(existing)

    sub = Subscription(
        user_id=user_id,
        target_type=body.target_type,
        target_id=body.target_id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return SubscriptionResponse.model_validate(sub)


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(
    sub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == sub_id,
            Subscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(sub)
    await db.commit()
