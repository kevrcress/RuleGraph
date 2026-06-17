"""Pydantic schemas for Rule responses."""
import uuid
from datetime import datetime
from typing import Any, Optional

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
    source_file: Optional[str] = None
    cognee_node_id: Optional[str] = None
    workitem_id: Optional[str] = None
    workitem_url: Optional[str] = None
    coverage_status: Optional[str] = None
    code_behavior: Optional[str] = None
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


class RuleCreate(BaseModel):
    title: str
    definition: str
    source_type: Optional[str] = "chat"


class RuleUpdate(BaseModel):
    title: Optional[str] = None
    definition: Optional[str] = None
    status: Optional[RuleStatusEnum] = None


class AuthoringAssist(BaseModel):
    type: str  # similarity|conflict|completeness|terminology
    message: str
    related_rule_id: Optional[uuid.UUID] = None


class RuleCreateResponse(BaseModel):
    id: uuid.UUID
    title: str
    definition: str
    status: RuleStatusEnum
    owner_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    authoring_assists: list[AuthoringAssist] = []

    model_config = {"from_attributes": True}


class LineageEvent(BaseModel):
    id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    definition: str
    status: Optional[RuleStatusEnum] = None
    changed_by: Optional[uuid.UUID] = None
    changed_at: Optional[datetime] = None
    change_note: Optional[str] = None
    rejection_note: Optional[str] = None

    model_config = {"from_attributes": True}


class LineageResponse(BaseModel):
    rule_id: uuid.UUID
    events: list[LineageEvent]


class RejectRequest(BaseModel):
    rejection_note: str


class WorkItemRequest(BaseModel):
    workitem_title: str
    workitem_body: str
    repo: Optional[str] = None
    project: Optional[str] = None
