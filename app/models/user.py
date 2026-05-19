"""User and ConnectedAccount models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # admin|business_admin|tech_lead|user
    aad_object_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    connected_accounts: Mapped[list["ConnectedAccount"]] = relationship(
        "ConnectedAccount", back_populates="user", cascade="all, delete-orphan"
    )
    rules: Mapped[list["Rule"]] = relationship("Rule", back_populates="owner", foreign_keys="Rule.owner_id")


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    pat_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    org: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="connected_accounts")
