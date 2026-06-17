"""Pydantic schemas for ingest-related endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.ingest import IngestErrorSourceEnum


class IngestFileResponse(BaseModel):
    """Response from POST /ingest/file."""
    status: str
    rules_extracted: int
    run_id: str


class IngestErrorItem(BaseModel):
    """Schema for ingest error list items."""
    id: uuid.UUID
    source_name: Optional[str] = None
    file_path: Optional[str] = None
    error_source: Optional[IngestErrorSourceEnum] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    raw_content: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedIngestErrors(BaseModel):
    """Paginated response for ingest errors."""
    items: list[IngestErrorItem]
    total: int
