"""Subscription and Notification models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, Boolean, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    rule: Mapped[Optional["Rule"]] = relationship("Rule")
