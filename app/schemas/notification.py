"""Pydantic schemas for Subscriptions and Notifications."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    target_type: str  # 'rule'|'service'|'conflict'|'coverage_gap'
    target_id: uuid.UUID


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    target_type: str
    target_id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedSubscriptions(BaseModel):
    items: list[SubscriptionResponse]
    total: int
    page: int
    limit: int


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    type: str
    rule_id: Optional[uuid.UUID] = None
    message: str
    read: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedNotifications(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    limit: int


class ChatMessage(BaseModel):
    message: str
    session_id: str
    view: str = "business"  # 'business'|'technical'


class ChatSource(BaseModel):
    type: str  # 'rule'|'document'|'service'
    id: Optional[str] = None
    title: str


class ChatResponse(BaseModel):
    message: str
    confidence: float
    sources: list[ChatSource] = []
    session_id: str


class ChatHistoryMessage(BaseModel):
    role: str  # 'user'|'assistant'
    content: str
    confidence: Optional[float] = None
    sources: list[ChatSource] = []
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage]
