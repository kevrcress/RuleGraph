"""Pydantic schemas for terminology endpoints."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field


class TerminologyOut(BaseModel):
    id: uuid.UUID
    canonical_term: Optional[str] = None
    variants: list[str]
    services: list[str]
    status: Optional[str] = None
    definition: Optional[str] = None
    definition_confidence: Optional[float] = None
    definition_status: Optional[str] = None  # draft | accepted | edited
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    @computed_field
    @property
    def is_issue(self) -> bool:
        """True when the same concept is named differently across 2+ services."""
        return len(self.services) >= 2 and len(set(self.variants)) > 1

    model_config = {"from_attributes": True}


class TerminologyDefinitionUpdate(BaseModel):
    definition: Optional[str] = None
    definition_status: Optional[str] = None  # accepted | edited


class PaginatedTerminology(BaseModel):
    items: list[TerminologyOut]
    total: int
    page: int
    limit: int
