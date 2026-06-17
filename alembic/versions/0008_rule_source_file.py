"""Add source_file column to rules table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("rules", sa.Column("source_file", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rules", "source_file")
