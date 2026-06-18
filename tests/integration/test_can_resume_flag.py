"""Guard test for the server-authoritative ``can_resume`` flag on GET /admin/sources.

Resumability is decided server-side via ``is_run_resumable`` (the same predicate the
``/resume`` endpoint gates on) AND "some files still outstanding" (done < total). The
frontend reads ``can_resume`` directly so the Resume button can never offer a resume the
server would reject. This asserts:

- an errored run with an outstanding (error) checkpoint  → can_resume = True
- a cleanly completed run with all checkpoints done      → can_resume = False

Teardown deletes checkpoint rows before run rows — the checkpoints FK has no CASCADE.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete

from app.models.ingest import IngestFileCheckpoint, IngestRun
from app.models.ingest_source import IngestSource


class TestCanResumeFlag:

    async def test_list_route_reports_can_resume(self, client, seeded_users, db_session):
        db = db_session
        suffix = uuid.uuid4().hex[:8]
        resumable_name = f"resumable-{suffix}"
        done_name = f"done-{suffix}"
        now = datetime.now(timezone.utc)

        # Resumable: source in error, run completed_with_errors, one file done + one errored
        # (done=1 < total=2 → outstanding work remains).
        resumable_src = IngestSource(
            id=uuid.uuid4(), name=resumable_name, source_type="github_repo",
            repo_url="https://example.com/r.git", branch="main", ingest_status="error",
        )
        # Clean: source idle, run completed, the only checkpoint is done (done=1 == total=1).
        done_src = IngestSource(
            id=uuid.uuid4(), name=done_name, source_type="github_repo",
            repo_url="https://example.com/r.git", branch="main", ingest_status="idle",
        )
        db.add_all([resumable_src, done_src])

        resumable_run = IngestRun(
            id=uuid.uuid4(), source_name=resumable_name, status="completed_with_errors",
            started_at=now, files_processed=1, files_errored=1,
        )
        done_run = IngestRun(
            id=uuid.uuid4(), source_name=done_name, status="completed",
            started_at=now, files_processed=1, files_errored=0,
        )
        db.add_all([resumable_run, done_run])
        await db.flush()

        db.add_all([
            IngestFileCheckpoint(id=uuid.uuid4(), ingest_run_id=resumable_run.id,
                                 file_path="a.py", status="done", processed_at=now),
            IngestFileCheckpoint(id=uuid.uuid4(), ingest_run_id=resumable_run.id,
                                 file_path="b.py", status="error", processed_at=now,
                                 error_message="boom"),
            IngestFileCheckpoint(id=uuid.uuid4(), ingest_run_id=done_run.id,
                                 file_path="c.py", status="done", processed_at=now),
        ])
        await db.commit()

        try:
            r = await client.get(
                "/admin/sources?limit=200",
                headers={"Authorization": f"Bearer {seeded_users['admin']}"},
            )
            assert r.status_code == 200, r.text
            by_name = {item["name"]: item for item in r.json()["items"]}

            assert by_name[resumable_name]["can_resume"] is True
            assert by_name[done_name]["can_resume"] is False
        finally:
            run_ids = [resumable_run.id, done_run.id]
            await db.execute(
                delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id.in_(run_ids))
            )
            await db.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
            await db.execute(
                delete(IngestSource).where(IngestSource.name.in_([resumable_name, done_name]))
            )
            await db.commit()
