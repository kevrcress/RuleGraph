"""Add summary column to services table.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("services", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("services", "summary")
