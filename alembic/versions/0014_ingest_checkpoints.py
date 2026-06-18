"""Add ingest_file_checkpoints table and batch columns to ingest_runs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")

    op.create_table(
        "ingest_file_checkpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ingest_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingest_runs.id"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "ingest_run_id", "file_path", name="uq_ingest_file_checkpoints_run_path"
        ),
    )
    op.create_index(
        "ix_ingest_file_checkpoints_run_status",
        "ingest_file_checkpoints",
        ["ingest_run_id", "status"],
    )

    op.add_column("ingest_runs", sa.Column("batch_id", sa.Text(), nullable=True))
    op.add_column(
        "ingest_runs",
        sa.Column("batch_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("ingest_runs", sa.Column("batch_status", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_runs", "batch_status")
    op.drop_column("ingest_runs", "batch_submitted_at")
    op.drop_column("ingest_runs", "batch_id")
    op.drop_index(
        "ix_ingest_file_checkpoints_run_status",
        table_name="ingest_file_checkpoints",
    )
    op.drop_table("ingest_file_checkpoints")
