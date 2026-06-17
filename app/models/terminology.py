"""TerminologyInconsistency model for cross-service naming variants."""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TerminologyInconsistency(Base):
    __tablename__ = "terminology_inconsistencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_term: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variants: Mapped[List[str]] = mapped_column(ARRAY(Text()), nullable=False)
    services: Mapped[List[str]] = mapped_column(ARRAY(Text()), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="pending")  # pending|approved|rejected
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    definition_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    definition_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # draft|accepted|edited
    detected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
