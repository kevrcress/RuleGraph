"""Stage 2 schema additions: conflicts, terminology_inconsistencies, coverage_status on rules.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    # Add coverage_status to rules
    op.add_column(
        "rules",
        sa.Column("coverage_status", sa.Text(), nullable=True, server_default="uncovered"),
    )

    # Create conflicts table
    op.create_table(
        "conflicts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("services", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("rule_ids", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True, server_default="medium"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create terminology_inconsistencies table
    op.create_table(
        "terminology_inconsistencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("canonical_term", sa.Text(), nullable=True),
        sa.Column("variants", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("services", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("terminology_inconsistencies")
    op.drop_table("conflicts")
    op.drop_column("rules", "coverage_status")
