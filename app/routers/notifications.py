"""
Notifications router — GET /notifications, PUT /notifications/{id}/read.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.notification import NotificationResponse, PaginatedNotifications
from app.services import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedNotifications)
async def list_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    items, total = await notification_service.get_notifications(
        db, user_id, page=page, limit=limit
    )
    return PaginatedNotifications(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("/{note_id}/read", response_model=NotificationResponse)
async def mark_read(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    note = await notification_service.mark_notification_read(db, note_id, user_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationResponse.model_validate(note)
