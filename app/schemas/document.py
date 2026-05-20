"""Pydantic schemas for document endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    status: str
    owner_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    uploaded_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    limit: int


class DocumentPreviewResponse(BaseModel):
    proposed_new_rules: list[dict]
    proposed_rule_changes: list[dict]
    context_additions: list[dict]
    conflicts_detected: list[dict]
    document_stored_as: str
