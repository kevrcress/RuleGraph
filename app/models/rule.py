"""Rule, RuleVersion, Service, and RuleService models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Float, func, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class RuleStatusEnum(str, enum.Enum):
    proposed = "proposed"
    under_review = "under_review"
    approved = "approved"
    active = "active"
    drift = "drift"
    needs_update = "needs_update"
    deprecated = "deprecated"


class EnvironmentTypeEnum(str, enum.Enum):
    dev = "dev"
    uat = "uat"
    prod = "prod"


# PostgreSQL native enum types
# create_type=True so that Base.metadata.create_all() (used in tests) creates the types.
# The Alembic migration creates them manually (with DO $$ EXCEPTION blocks) before table creation.
rule_status_pg = SAEnum(
    RuleStatusEnum,
    name="rule_status",
    create_type=True,
)

environment_type_pg = SAEnum(
    EnvironmentTypeEnum,
    name="environment_type",
    create_type=True,
)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[RuleStatusEnum] = mapped_column(
        rule_status_pg, nullable=False, default=RuleStatusEnum.proposed
    )
    environment: Mapped[Optional[EnvironmentTypeEnum]] = mapped_column(
        environment_type_pg, nullable=True
    )
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    graph_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cognee_node_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workitem_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workitem_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="rules", foreign_keys=[owner_id])
    versions: Mapped[list["RuleVersion"]] = relationship("RuleVersion", back_populates="rule")
    rule_services: Mapped[list["RuleService"]] = relationship("RuleService", back_populates="rule")
    rule_documents: Mapped[list["RuleDocument"]] = relationship("RuleDocument", back_populates="rule")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id"), nullable=True
    )
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[RuleStatusEnum]] = mapped_column(rule_status_pg, nullable=True)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    change_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    rule: Mapped[Optional["Rule"]] = relationship("Rule", back_populates="versions")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    rule_services: Mapped[list["RuleService"]] = relationship("RuleService", back_populates="service")


class RuleService(Base):
    __tablename__ = "rule_services"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule", back_populates="rule_services")
    service: Mapped["Service"] = relationship("Service", back_populates="rule_services")
