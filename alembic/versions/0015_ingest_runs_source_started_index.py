"""Add composite index on ingest_runs(source_name, started_at).

The hot "latest run for a source" query — WHERE source_name = ? ORDER BY started_at
DESC, id DESC LIMIT 1 — runs from the resume gate, the staleness recovery sweep, and
the admin sources list (latest_run_for_source). The index columns are ordered DESC to
match that access pattern exactly (incl. the id tiebreaker) so Postgres serves it
without a sort. Without this index those are full scans + sort on a growing table.

NOTE: this migration was amended in-branch (the original created the index ASC without
the id tiebreaker). A dev DB already at head must `alembic downgrade 0014 && alembic
upgrade head` to pick up the corrected definition. See PR-review IV-025.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.create_index(
        "ix_ingest_runs_source_started",
        "ingest_runs",
        ["source_name", sa.text("started_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_source_started", table_name="ingest_runs")
