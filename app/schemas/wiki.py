"""Pydantic schemas for the built-in wiki."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WikiPageItem(BaseModel):
    id: uuid.UUID
    module: str
    title: str
    content: str
    linked_rule_ids: list[str] = []
    last_generated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WikiPageDetail(WikiPageItem):
    linked_rules: list[dict] = []


class PaginatedWikiPages(BaseModel):
    items: list[WikiPageItem]
    total: int
    page: int
    limit: int
