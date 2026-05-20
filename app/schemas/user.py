"""User schemas for API responses."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    name: str
    role: str
    aad_object_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    username: str
    email: str
    name: str
    password: str
    role: str = "user"


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


class PaginatedUsers(BaseModel):
    items: list[UserResponse]
    total: int
    page: int = 1
    limit: int = 50
