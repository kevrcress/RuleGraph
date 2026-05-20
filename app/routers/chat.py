"""
Chat router — POST /chat, GET /chat/history.
Rate limited to 60 requests/hour per user per Section 27.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.notification import ChatMessage, ChatResponse, ChatHistoryResponse
from app.services import chat_service
from app.security.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_CHAT_LIMIT = 60
_CHAT_WINDOW = 3600  # 1 hour in seconds


@router.post("", response_model=ChatResponse)
async def send_chat(
    body: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    rl_key = f"chat:{user_id}"
    allowed, remaining = await check_rate_limit(rl_key, _CHAT_LIMIT, _CHAT_WINDOW)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Chat rate limit exceeded. Try again later.",
            headers={"Retry-After": "3600"},
        )

    return await chat_service.chat(
        db=db,
        user_id=user_id,
        session_id=body.session_id,
        message=body.message,
        view=body.view,
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["sub"])
    return await chat_service.get_history(user_id=user_id, session_id=session_id)
