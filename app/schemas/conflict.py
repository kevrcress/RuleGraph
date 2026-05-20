"""Pydantic schemas for conflict endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConflictOut(BaseModel):
    id: uuid.UUID
    description: str
    services: list[str]
    rule_ids: Optional[list[str]] = None
    severity: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedConflicts(BaseModel):
    items: list[ConflictOut]
    total: int
    page: int
    limit: int
