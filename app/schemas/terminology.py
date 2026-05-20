"""Pydantic schemas for terminology endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TerminologyOut(BaseModel):
    id: uuid.UUID
    canonical_term: Optional[str] = None
    variants: list[str]
    services: list[str]
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedTerminology(BaseModel):
    items: list[TerminologyOut]
    total: int
    page: int
    limit: int
