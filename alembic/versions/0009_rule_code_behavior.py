"""Add code_behavior column to rules table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("rules", sa.Column("code_behavior", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rules", "code_behavior")
