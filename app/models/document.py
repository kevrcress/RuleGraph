"""Document and RuleDocument models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="sandbox")
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    rule_documents: Mapped[list["RuleDocument"]] = relationship("RuleDocument", back_populates="document")


class RuleDocument(Base):
    __tablename__ = "rule_documents"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule", back_populates="rule_documents")
    document: Mapped["Document"] = relationship("Document", back_populates="rule_documents")
