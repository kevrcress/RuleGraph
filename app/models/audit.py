"""AuditLog model."""
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Text, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    detail: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
