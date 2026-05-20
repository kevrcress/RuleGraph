"""Pydantic schemas for Rule responses."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.rule import RuleStatusEnum, EnvironmentTypeEnum


class RuleListItem(BaseModel):
    """Schema for items in the paginated rules list."""
    id: uuid.UUID
    title: str
    definition: str
    status: RuleStatusEnum
    extraction_confidence: Optional[float] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RuleDetail(BaseModel):
    """Schema for the full rule detail endpoint."""
    id: uuid.UUID
    title: str
    definition: str
    owner_id: Optional[uuid.UUID] = None
    status: RuleStatusEnum
    environment: Optional[EnvironmentTypeEnum] = None
    extraction_confidence: Optional[float] = None
    graph_quality_score: Optional[float] = None
    source_type: Optional[str] = None
    cognee_node_id: Optional[str] = None
    workitem_id: Optional[str] = None
    workitem_url: Optional[str] = None
    coverage_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedRules(BaseModel):
    """Paginated response for rules list."""
    items: list[RuleListItem]
    total: int
    page: int
    limit: int
