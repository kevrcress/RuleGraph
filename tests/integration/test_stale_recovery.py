"""Integration tests for staleness-based ingest recovery (Phase 2).

Seeds one STALE ingesting source (run started far in the past, no recent
checkpoint) and one FRESH ingesting source (recent checkpoint), then asserts
``reset_stale_ingests`` resets ONLY the stale one to "error", marks its run
resumable ("completed_with_errors"), and returns exactly that one name.

Teardown deletes checkpoint rows before run rows — the checkpoints FK has no
ON DELETE CASCADE.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.config import settings
from app.models.ingest import IngestFileCheckpoint, IngestRun
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


class TestStaleRecovery:

    async def test_resets_only_stale_ingesting_source(self, db_session):
        db = db_session
        suffix = uuid.uuid4().hex[:8]
        stale_name = f"stale-src-{suffix}"
        fresh_name = f"fresh-src-{suffix}"

        # Well beyond timeout + grace so the stale run is unambiguously stale.
        far_past = datetime.now(timezone.utc) - timedelta(
            seconds=settings.ingest_job_timeout_seconds + 10_000
        )

        stale_src = _source(stale_name)
        fresh_src = _source(fresh_name)
        db.add_all([stale_src, fresh_src])

        # Stale run: started long ago, with an old checkpoint (no recent progress).
        stale_run = IngestRun(
            id=uuid.uuid4(), source_name=stale_name, status="running",
            started_at=far_past, files_processed=0, files_errored=0,
        )
        # Fresh run: started long ago BUT with a just-now checkpoint → not stale.
        fresh_run = IngestRun(
            id=uuid.uuid4(), source_name=fresh_name, status="running",
            started_at=far_past, files_processed=1, files_errored=0,
        )
        db.add_all([stale_run, fresh_run])
        await db.flush()

        db.add(IngestFileCheckpoint(
            id=uuid.uuid4(), ingest_run_id=stale_run.id, file_path="old/file.py",
            status="done", processed_at=far_past,
        ))
        db.add(IngestFileCheckpoint(
            id=uuid.uuid4(), ingest_run_id=fresh_run.id, file_path="recent/file.py",
            status="done", processed_at=datetime.now(timezone.utc),
        ))
        await db.commit()

        try:
            reset = await reset_stale_ingests(db)

            assert reset == [stale_name], f"expected only {stale_name} reset, got {reset}"

            await db.refresh(stale_src)
            await db.refresh(fresh_src)
            await db.refresh(stale_run)
            await db.refresh(fresh_run)

            # Stale source recovered to error, run made resumable.
            assert stale_src.ingest_status == "error"
            assert stale_src.ingest_error == (
                "Ingest worker stopped responding (stale; auto-recovered)"
            )
            assert stale_run.status == "completed_with_errors"

            # Fresh source untouched.
            assert fresh_src.ingest_status == "ingesting"
            assert fresh_src.ingest_error is None
            assert fresh_run.status == "running"
        finally:
            run_ids = [stale_run.id, fresh_run.id]
            await db.execute(
                delete(IngestFileCheckpoint).where(
                    IngestFileCheckpoint.ingest_run_id.in_(run_ids)
                )
            )
            await db.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
            await db.execute(
                delete(IngestSource).where(
                    IngestSource.name.in_([stale_name, fresh_name])
                )
            )
            await db.commit()
