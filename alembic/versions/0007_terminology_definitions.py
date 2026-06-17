"""Add definition fields to terminology_inconsistencies.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column("terminology_inconsistencies", sa.Column("definition", sa.Text(), nullable=True))
    op.add_column("terminology_inconsistencies", sa.Column("definition_confidence", sa.Float(), nullable=True))
    op.add_column(
        "terminology_inconsistencies",
        sa.Column("definition_status", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("terminology_inconsistencies", "definition_status")
    op.drop_column("terminology_inconsistencies", "definition_confidence")
    op.drop_column("terminology_inconsistencies", "definition")
