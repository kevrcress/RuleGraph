"""
Notification creation and delivery per Section 18.
All in-app only (Phase 1). Phase 2 adds email/Slack.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, Subscription

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    message: str,
    rule_id: Optional[uuid.UUID] = None,
) -> Notification:
    note = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        rule_id=rule_id,
        read=False,
    )
    db.add(note)
    await db.flush()
    return note


async def notify_subscribers(
    db: AsyncSession,
    target_type: str,
    target_id: uuid.UUID,
    notification_type: str,
    message: str,
    rule_id: Optional[uuid.UUID] = None,
    exclude_user_id: Optional[uuid.UUID] = None,
) -> int:
    """Create notifications for all subscribers of a target. Returns count created."""
    q = select(Subscription).where(
        Subscription.target_type == target_type,
        Subscription.target_id == target_id,
    )
    result = await db.execute(q)
    subs = result.scalars().all()

    count = 0
    for sub in subs:
        if sub.user_id is None:
            continue
        if exclude_user_id and sub.user_id == exclude_user_id:
            continue
        await create_notification(
            db,
            user_id=sub.user_id,
            notification_type=notification_type,
            message=message,
            rule_id=rule_id,
        )
        count += 1

    return count


async def notify_rule_status_change(
    db: AsyncSession,
    rule_id: uuid.UUID,
    new_status: str,
    actor_id: Optional[uuid.UUID] = None,
) -> None:
    """Fire notifications for rule status changes to all rule subscribers."""
    type_map = {
        "drift": "rule_drift",
        "approved": "rule_approved",
        "proposed": "rule_returned",
        "active": "rule_active",
        "deprecated": "rule_deprecated",
    }
    notification_type = type_map.get(new_status, "rule_status_change")

    messages = {
        "drift": "A rule you subscribed to has drifted from its defined behaviour.",
        "approved": "A rule you subscribed to has been approved.",
        "proposed": "A rule you subscribed to has been returned for revision.",
        "active": "A rule you subscribed to is now active.",
        "deprecated": "A rule you subscribed to has been deprecated.",
    }
    message = messages.get(
        new_status,
        f"A rule you subscribed to changed status to {new_status}.",
    )

    count = await notify_subscribers(
        db,
        target_type="rule",
        target_id=rule_id,
        notification_type=notification_type,
        message=message,
        rule_id=rule_id,
        exclude_user_id=actor_id,
    )
    if count:
        logger.info("Sent %d notifications for rule %s → %s", count, rule_id, new_status)


async def get_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[Notification], int]:
    offset = (page - 1) * limit

    count_q = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = (await db.execute(items_q)).scalars().all()
    return list(items), total


async def mark_notification_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[Notification]:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    note = result.scalar_one_or_none()
    if note is None:
        return None
    note.read = True
    await db.commit()
    await db.refresh(note)
    return note
