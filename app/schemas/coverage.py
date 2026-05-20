"""Pydantic schemas for coverage endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CoverageItem(BaseModel):
    id: uuid.UUID
    title: str
    definition: str
    coverage_status: str
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedCoverage(BaseModel):
    items: list[CoverageItem]
    total: int
    page: int
    limit: int
