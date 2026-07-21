"""Integration tests for ingest file-status endpoints.

Covers:
  GET  /admin/sources/{id}/ingest-runs/latest/files  (get_latest_ingest_files)
  POST /admin/sources/{id}/retry-errors              (retry_errors_ingest)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from sqlalchemy import delete, select

from app.main import app
from app.models.ingest import IngestFileCheckpoint, IngestRun
from app.models.ingest_source import IngestSource
from app.tasks.queue import INGEST_QUEUE_NAME


async def _create_source(client, seeded_users, name: str) -> str:
    """Create a source via the API and return its UUID string."""
    r = await client.post(
        "/admin/sources",
        json={
            "name": name,
            "source_type": "github_repo",
            "repo_url": "https://example.com/r.git",
            "branch": "main",
        },
        headers={"Authorization": f"Bearer {seeded_users['admin']}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _delete_source(client, seeded_users, source_id: str) -> None:
    """Delete a source via the API."""
    await client.delete(
        f"/admin/sources/{source_id}",
        headers={"Authorization": f"Bearer {seeded_users['admin']}"},
    )


class TestGetLatestIngestFiles:

    async def test_no_run_returns_empty(self, client, seeded_users):
        name = f"files-empty-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        r = await client.get(
            f"/admin/sources/{source_id}/ingest-runs/latest/files",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["run"] is None

        await _delete_source(client, seeded_users, source_id)

    async def test_returns_checkpoints_with_run(self, client, seeded_users, db_session):
        name = f"files-with-run-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(),
            source_name=name,
            status="completed",
            files_processed=1,
            files_errored=1,
        )
        db_session.add(run)
        await db_session.commit()

        cp_done = IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/a.py",
            status="done",
        )
        cp_error = IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/b.py",
            status="error",
            error_message="extraction failed",
        )
        db_session.add(cp_done)
        db_session.add(cp_error)
        await db_session.commit()

        r = await client.get(
            f"/admin/sources/{source_id}/ingest-runs/latest/files",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 2
        assert body["run"] is not None
        assert body["run"]["files_errored"] == 1

        paths = {item["file_path"] for item in body["items"]}
        statuses = {item["file_path"]: item["status"] for item in body["items"]}
        assert "src/a.py" in paths
        assert "src/b.py" in paths
        assert statuses["src/a.py"] == "done"
        assert statuses["src/b.py"] == "error"

        # Clean up: checkpoints before run (FK constraint)
        await db_session.execute(
            delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id == run.id)
        )
        await db_session.execute(delete(IngestRun).where(IngestRun.id == run.id))
        await db_session.commit()
        await _delete_source(client, seeded_users, source_id)

    async def test_pagination(self, client, seeded_users, db_session):
        name = f"files-paged-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(),
            source_name=name,
            status="completed",
            files_processed=3,
            files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        for i in range(3):
            db_session.add(IngestFileCheckpoint(
                id=uuid.uuid4(),
                ingest_run_id=run.id,
                file_path=f"src/file_{i}.py",
                status="done",
            ))
        await db_session.commit()

        r1 = await client.get(
            f"/admin/sources/{source_id}/ingest-runs/latest/files?page=1&page_size=2",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        assert len(body1["items"]) == 2
        assert body1["total"] == 3

        r2 = await client.get(
            f"/admin/sources/{source_id}/ingest-runs/latest/files?page=2&page_size=2",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert len(body2["items"]) == 1
        assert body2["total"] == 3

        await db_session.execute(
            delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id == run.id)
        )
        await db_session.execute(delete(IngestRun).where(IngestRun.id == run.id))
        await db_session.commit()
        await _delete_source(client, seeded_users, source_id)


class TestRetryErrorsEndpoint:

    async def test_404_source_not_found(self, client, seeded_users):
        random_id = uuid.uuid4()
        r = await client.post(
            f"/admin/sources/{random_id}/retry-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 404, r.text

    async def test_409_ingesting(self, client, seeded_users, db_session):
        name = f"retry-409-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        # Set ingest_status = "ingesting" directly
        result = await db_session.execute(
            select(IngestSource).where(IngestSource.id == uuid.UUID(source_id))
        )
        src = result.scalar_one()
        src.ingest_status = "ingesting"
        await db_session.commit()

        r = await client.post(
            f"/admin/sources/{source_id}/retry-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 409, r.text
        assert "in progress" in r.json()["detail"].lower()

        # Restore and clean up
        src.ingest_status = "idle"
        await db_session.commit()
        await _delete_source(client, seeded_users, source_id)

    async def test_400_no_error_checkpoints(self, client, seeded_users, db_session):
        name = f"retry-400-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(),
            source_name=name,
            status="completed",
            files_processed=1,
            files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        db_session.add(IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/good.py",
            status="done",
        ))
        await db_session.commit()

        r = await client.post(
            f"/admin/sources/{source_id}/retry-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 400, r.text
        assert "no errored files" in r.json()["detail"].lower()

        await db_session.execute(
            delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id == run.id)
        )
        await db_session.execute(delete(IngestRun).where(IngestRun.id == run.id))
        await db_session.commit()
        await _delete_source(client, seeded_users, source_id)

    async def test_success_resets_errors_and_enqueues(self, client, seeded_users, db_session):
        name = f"retry-ok-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(),
            source_name=name,
            status="completed",
            files_processed=1,
            files_errored=2,
        )
        db_session.add(run)
        await db_session.commit()

        cp_done = IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/good.py",
            status="done",
        )
        cp_err1 = IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/bad1.py",
            status="error",
            error_message="extraction failed",
        )
        cp_err2 = IngestFileCheckpoint(
            id=uuid.uuid4(),
            ingest_run_id=run.id,
            file_path="src/bad2.py",
            status="error",
            error_message="timeout",
        )
        db_session.add(cp_done)
        db_session.add(cp_err1)
        db_session.add(cp_err2)
        await db_session.commit()

        app.state.arq_pool.enqueue_job = AsyncMock()

        r = await client.post(
            f"/admin/sources/{source_id}/retry-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "queued"
        assert body["run_id"] is not None

        # Verify error checkpoints reset to "pending"
        await db_session.refresh(cp_err1)
        await db_session.refresh(cp_err2)
        assert cp_err1.status == "pending"
        assert cp_err2.status == "pending"

        # Verify done checkpoint untouched
        await db_session.refresh(cp_done)
        assert cp_done.status == "done"

        # Verify arq job enqueued with resume=True
        app.state.arq_pool.enqueue_job.assert_awaited_once_with(
            "run_source_ingest", str(source_id), True, _queue_name=INGEST_QUEUE_NAME
        )

        # Verify run status updated to "running"
        await db_session.refresh(run)
        assert run.status == "running"

        await db_session.execute(
            delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id == run.id)
        )
        await db_session.execute(delete(IngestRun).where(IngestRun.id == run.id))
        await db_session.commit()
        await _delete_source(client, seeded_users, source_id)
