"""Add ingest_progress to ingest_sources.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("ingest_sources", sa.Column("ingest_progress", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_sources", "ingest_progress")
