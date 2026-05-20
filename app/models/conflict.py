"""Conflict model for cross-service rule conflicts."""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Conflict(Base):
    __tablename__ = "conflicts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    services: Mapped[List[str]] = mapped_column(ARRAY(Text()), nullable=False)
    rule_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text()), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="medium")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ingest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
