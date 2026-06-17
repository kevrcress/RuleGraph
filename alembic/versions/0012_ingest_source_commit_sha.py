"""Add last_commit_sha to ingest_sources.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("ingest_sources", sa.Column("last_commit_sha", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_sources", "last_commit_sha")
