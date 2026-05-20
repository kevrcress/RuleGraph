"""Pydantic schemas for diff endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DiffItem(BaseModel):
    rule_id: uuid.UUID
    title: str
    status: str
    change_type: str
    changed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedDiff(BaseModel):
    items: list[DiffItem]
    total: int
    page: int
    limit: int


class DiffVersion(BaseModel):
    definition: str
    status: Optional[str] = None
    changed_at: Optional[datetime] = None
    change_note: Optional[str] = None


class DiffDetail(BaseModel):
    rule_id: uuid.UUID
    rule_title: str
    before: Optional[DiffVersion] = None
    after: Optional[DiffVersion] = None
    versions: list[DiffVersion] = []
