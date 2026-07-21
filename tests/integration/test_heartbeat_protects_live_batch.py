"""Integration test for the Batch poll-phase heartbeat (DEC-045).

During the Anthropic Batches poll phase no per-file checkpoints are written, so a
long-running-but-alive batch would look stale to ``reset_stale_ingests``. The poll
loop bumps ``IngestRun.last_heartbeat_at`` instead; ``is_run_stale`` folds it into
``last_progress``. This test asserts a run whose only "progress" is a recent
heartbeat is NOT reset, and that the same run with an old heartbeat IS reset.

Teardown deletes run rows after source rows (no checkpoints created here).
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.config import settings
from app.models.ingest import IngestRun
from app.models.ingest_source import IngestSource
from app.tasks.recovery import reset_stale_ingests


def _source(name: str) -> IngestSource:
    return IngestSource(
        id=uuid.uuid4(),
        name=name,
        source_type="github_repo",
        repo_url="https://example.com/r.git",
        branch="main",
        ingest_status="ingesting",
    )


class TestHeartbeatProtectsLiveBatch:

    async def test_recent_heartbeat_prevents_reset_old_heartbeat_allows_it(self, db_session):
        db = db_session
        name = f"live-batch-{uuid.uuid4().hex[:8]}"

        # started_at is far past (no checkpoints written during the poll phase), so
        # without a heartbeat this run would be unambiguously stale.
        far_past = datetime.now(timezone.utc) - timedelta(
            seconds=settings.ingest_job_timeout_seconds + 10_000
        )

        src = _source(name)
        run = IngestRun(
            id=uuid.uuid4(), source_name=name, status="running",
            started_at=far_past, files_processed=0, files_errored=0,
            batch_id="msgbatch_test", batch_status="in_progress",
            last_heartbeat_at=datetime.now(timezone.utc),  # alive: just polled
        )
        db.add_all([src, run])
        await db.commit()

        try:
            # Recent heartbeat → run is alive → NOT reset.
            reset = await reset_stale_ingests(db)
            assert name not in reset, f"live-heartbeat run was wrongly reset: {reset}"
            await db.refresh(src)
            await db.refresh(run)
            assert src.ingest_status == "ingesting"
            assert run.status == "running"

            # Now age the heartbeat past the threshold → genuinely dead → IS reset.
            run.last_heartbeat_at = far_past
            await db.commit()

            reset = await reset_stale_ingests(db)
            assert name in reset, f"dead-heartbeat run was not reset: {reset}"
            await db.refresh(src)
            await db.refresh(run)
            assert src.ingest_status == "error"
            assert run.status == "completed_with_errors"
        finally:
            await db.execute(delete(IngestRun).where(IngestRun.id == run.id))
            await db.execute(delete(IngestSource).where(IngestSource.name == name))
            await db.commit()
