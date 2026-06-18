"""Guard test for Phase 5 — ``run_is_stale`` on the GET /admin/sources list route.

A source stuck at ``ingest_status="ingesting"`` whose latest run is STALE must
surface ``run_is_stale=true`` so the frontend can enable Resume immediately —
without waiting for the 5-minute recovery cron to flip the source to ``error``.
A source whose run is FRESH (recent checkpoint) must report ``run_is_stale=false``
so a healthy in-flight run does not get a Resume button (no double-enqueue).

Seeding mirrors tests/integration/test_stale_recovery.py (Phase 2): one stale and
one fresh ``ingesting`` source, asserting the same staleness predicate the cron
sweep uses now flows through ``_latest_run_progress`` onto the API response.

Teardown deletes checkpoint rows before run rows — the checkpoints FK has no
ON DELETE CASCADE.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.config import settings
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


class TestRunIsStaleFlag:

    async def test_list_route_reports_run_is_stale(self, client, seeded_users, db_session):
        db = db_session
        suffix = uuid.uuid4().hex[:8]
        stale_name = f"stale-flag-{suffix}"
        fresh_name = f"fresh-flag-{suffix}"

        # Well beyond timeout + grace so the stale run is unambiguously stale.
        far_past = datetime.now(timezone.utc) - timedelta(
            seconds=settings.ingest_job_timeout_seconds + 10_000
        )

        stale_src = _source(stale_name)
        fresh_src = _source(fresh_name)
        db.add_all([stale_src, fresh_src])

        stale_run = IngestRun(
            id=uuid.uuid4(), source_name=stale_name, status="running",
            started_at=far_past, files_processed=0, files_errored=0,
        )
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
            r = await client.get(
                "/admin/sources?limit=200",
                headers={"Authorization": f"Bearer {seeded_users['admin']}"},
            )
            assert r.status_code == 200, r.text
            by_name = {item["name"]: item for item in r.json()["items"]}

            assert stale_name in by_name, f"{stale_name} missing from list response"
            assert fresh_name in by_name, f"{fresh_name} missing from list response"

            assert by_name[stale_name]["run_is_stale"] is True
            assert by_name[fresh_name]["run_is_stale"] is False
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
