"""IngestError and IngestRun models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, Integer, func, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class IngestErrorSourceEnum(str, enum.Enum):
    llm_extraction = "llm_extraction"
    cognee_ingest = "cognee_ingest"
    source_connector = "source_connector"
    document_parse = "document_parse"
    webhook = "webhook"


ingest_error_source_pg = SAEnum(
    IngestErrorSourceEnum,
    name="ingest_error_source",
    create_type=True,
)


class IngestError(Base):
    __tablename__ = "ingest_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_source: Mapped[Optional[IngestErrorSourceEnum]] = mapped_column(
        ingest_error_source_pg, nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_processed_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files_processed: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    files_errored: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    batch_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    batch_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    batch_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Bumped on every Batch poll so an actively-polling run (which writes no per-file
    # checkpoints during the poll phase) is not misjudged as stale. See DEC-045.
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class IngestFileCheckpoint(Base):
    __tablename__ = "ingest_file_checkpoints"
    __table_args__ = (
        UniqueConstraint("ingest_run_id", "file_path", name="uq_ingest_file_checkpoints_run_path"),
        Index("ix_ingest_file_checkpoints_run_status", "ingest_run_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ingest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_runs.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
