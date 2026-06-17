"""Add ingest_sources table for UI-managed repo source configuration.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.create_table(
        "ingest_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), unique=True, nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False, server_default="github_repo"),
        sa.Column("repo_url", sa.Text(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=False, server_default="main"),
        sa.Column("paths", ARRAY(sa.Text()), nullable=True),
        sa.Column("exclude", ARRAY(sa.Text()), nullable=True),
        sa.Column("test_paths", ARRAY(sa.Text()), nullable=True),
        sa.Column("pat_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_table("ingest_sources")
