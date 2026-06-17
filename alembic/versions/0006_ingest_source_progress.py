"""Add ingest_status and ingest_error columns to ingest_sources.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("ingest_sources", sa.Column("ingest_status", sa.Text(), nullable=False, server_default="idle"))
    op.add_column("ingest_sources", sa.Column("ingest_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_sources", "ingest_error")
    op.drop_column("ingest_sources", "ingest_status")
