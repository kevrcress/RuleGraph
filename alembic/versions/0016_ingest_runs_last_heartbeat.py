"""Add last_heartbeat_at to ingest_runs for poll-phase liveness.

During the Anthropic Batches poll phase no per-file checkpoints are written, so the
staleness predicate would see no progress and could flip a still-live batch to
``error``. The worker now bumps ``last_heartbeat_at`` on every poll; ``is_run_stale``
folds it into ``last_progress`` so an actively-polling run is never declared stale.
See DEC-045.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.add_column(
        "ingest_runs",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ingest_runs", "last_heartbeat_at")
