"""Add composite index on ingest_runs(source_name, started_at).

The hot "latest run for a source" query — WHERE source_name = ? ORDER BY started_at
DESC LIMIT 1 — runs from the resume gate, the staleness recovery sweep, and the admin
sources list. Without this index those are full scans + sort on a growing table.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-18
"""
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.create_index(
        "ix_ingest_runs_source_started",
        "ingest_runs",
        ["source_name", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_source_started", table_name="ingest_runs")
