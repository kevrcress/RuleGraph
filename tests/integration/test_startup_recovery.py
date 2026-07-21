"""Guard tests for the web-startup recovery entry point (Phase 3).

``app.main._reset_stuck_ingests`` must be staleness-aware: a uvicorn restart while
a worker is still legitimately ingesting must NOT false-flip a healthy in-flight
run to ``error`` (regression guard for the Phase-6 false-positive of prior work).
A genuinely stale ``ingesting`` source must still be reset.

``_reset_stuck_ingests`` opens its OWN session via the production
``app.database.async_session_factory`` (which targets the dev DB). To exercise it
against the test DB we monkeypatch that factory to one bound to ``test_engine``;
the function imports it at call-time, so patching the module attribute suffices.

Teardown deletes checkpoint rows before run rows — the checkpoints FK has no
ON DELETE CASCADE.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import app.database
from app.config import settings
from app.main import _reset_stuck_ingests
from app.models.ingest import IngestFileCheckpoint, IngestRun
from app.models.ingest_source import IngestSource


def _source(name: str) -> IngestSource:
    return IngestSource(
        id=uuid.uuid4(),
        name=name,
        source_type="github_repo",
        repo_url="https://example.com/r.git",
        branch="main",
        ingest_status="ingesting",
    )


class TestStartupRecovery:

    async def test_startup_resets_only_stale_ingesting_source(self, test_engine, monkeypatch):
        # Point the production factory the startup hook uses at the test engine.
        factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(app.database, "async_session_factory", factory)

        suffix = uuid.uuid4().hex[:8]
        stale_name = f"startup-stale-{suffix}"
        fresh_name = f"startup-fresh-{suffix}"

        far_past = datetime.now(timezone.utc) - timedelta(
            seconds=settings.ingest_job_timeout_seconds + 10_000
        )

        stale_run_id = uuid.uuid4()
        fresh_run_id = uuid.uuid4()

        async with factory() as db:
            db.add_all([_source(stale_name), _source(fresh_name)])
            db.add_all([
                IngestRun(
                    id=stale_run_id, source_name=stale_name, status="running",
                    started_at=far_past, files_processed=0, files_errored=0,
                ),
                IngestRun(
                    id=fresh_run_id, source_name=fresh_name, status="running",
                    started_at=far_past, files_processed=1, files_errored=0,
                ),
            ])
            await db.flush()
            db.add(IngestFileCheckpoint(
                id=uuid.uuid4(), ingest_run_id=stale_run_id, file_path="old/file.py",
                status="done", processed_at=far_past,
            ))
            db.add(IngestFileCheckpoint(
                id=uuid.uuid4(), ingest_run_id=fresh_run_id, file_path="recent/file.py",
                status="done", processed_at=datetime.now(timezone.utc),
            ))
            await db.commit()

        try:
            await _reset_stuck_ingests()

            async with factory() as db:
                stale_src = (await db.execute(
                    select(IngestSource).where(IngestSource.name == stale_name)
                )).scalar_one()
                fresh_src = (await db.execute(
                    select(IngestSource).where(IngestSource.name == fresh_name)
                )).scalar_one()
                stale_run = (await db.execute(
                    select(IngestRun).where(IngestRun.id == stale_run_id)
                )).scalar_one()
                fresh_run = (await db.execute(
                    select(IngestRun).where(IngestRun.id == fresh_run_id)
                )).scalar_one()

                # Stale source recovered; fresh in-flight source left untouched.
                assert stale_src.ingest_status == "error"
                assert stale_run.status == "completed_with_errors"
                assert fresh_src.ingest_status == "ingesting"
                assert fresh_src.ingest_error is None
                assert fresh_run.status == "running"
        finally:
            async with factory() as db:
                run_ids = [stale_run_id, fresh_run_id]
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
