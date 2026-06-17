"""IngestSource model — stores UI-managed repo configurations."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngestSource(Base):
    __tablename__ = "ingest_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="github_repo")
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(Text, nullable=False, default="main")
    paths: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    exclude: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    test_paths: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    pat_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    last_ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    ingest_status: Mapped[str] = mapped_column(Text, nullable=False, default="idle")
    ingest_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_progress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_commit_sha: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
