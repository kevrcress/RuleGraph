"""Guard tests for Phase 6 — arq worker enqueue + wrapper delegation.

Verifies:
  * POST /admin/sources/{id}/ingest enqueues run_source_ingest with (id, False).
  * POST /admin/sources/{id}/resume enqueues run_source_ingest with (id, True).
  * The arq wrapper run_source_ingest(ctx, ...) delegates to run_ingest_impl.

"survives uvicorn restart" is verified by-construction: the job runs in the arq
worker process (app/tasks/worker.py), not in the FastAPI BackgroundTasks pool, so
a backend restart does not kill an in-flight job. A full restart is a manual test.
"""
import uuid
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.ingest import IngestRun
from app.tasks.worker import INGEST_QUEUE_NAME, WorkerSettings


async def _create_source(client, seeded_users, name):
    r = await client.post(
        "/admin/sources",
        json={"name": name, "source_type": "github_repo", "repo_url": "https://example.com/r.git", "branch": "main"},
        headers={"Authorization": f"Bearer {seeded_users['admin']}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestEnqueue:

    async def test_trigger_enqueues_run_source_ingest(self, client, seeded_users):
        name = f"arq-trigger-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        app.state.arq_pool.enqueue_job = AsyncMock()
        r = await client.post(
            f"/admin/sources/{source_id}/ingest",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "started"
        app.state.arq_pool.enqueue_job.assert_awaited_once_with(
            "run_source_ingest", str(source_id), False, _queue_name=INGEST_QUEUE_NAME
        )

    async def test_resume_enqueues_run_source_ingest(self, client, seeded_users, db_session):
        name = f"arq-resume-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(), source_name=name, status="running",
            files_processed=0, files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        app.state.arq_pool.enqueue_job = AsyncMock()
        r = await client.post(
            f"/admin/sources/{source_id}/resume",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "resumed"
        app.state.arq_pool.enqueue_job.assert_awaited_once_with(
            "run_source_ingest", str(source_id), True, _queue_name=INGEST_QUEUE_NAME
        )

        from sqlalchemy import delete
        await db_session.execute(delete(IngestRun).where(IngestRun.source_name == name))
        await db_session.commit()


class TestWorkerWrapper:

    async def test_run_source_ingest_delegates_to_impl(self):
        from app.tasks import worker

        with patch.object(worker, "run_ingest_impl", AsyncMock(return_value=None)) as impl:
            await worker.run_source_ingest({}, "abc-123", True)

        impl.assert_awaited_once_with("abc-123", True)

    async def test_run_source_ingest_default_resume_false(self):
        from app.tasks import worker

        with patch.object(worker, "run_ingest_impl", AsyncMock(return_value=None)) as impl:
            await worker.run_source_ingest({}, "abc-123")

        impl.assert_awaited_once_with("abc-123", False)

    def test_worker_settings_max_tries_is_one(self):
        from app.tasks.worker import WorkerSettings

        assert WorkerSettings.max_tries == 1
        assert WorkerSettings.redis_settings is not None
        assert "run_source_ingest" in [f.__name__ for f in WorkerSettings.functions]


class TestQueueNameAlignment:
    """Guard against the silent enqueue no-op: enqueue sites must target the same
    queue the worker consumes (INGEST_QUEUE_NAME), or jobs land on arq's default
    queue and are never processed.
    """

    def test_worker_consumes_ingest_queue(self):
        assert WorkerSettings.queue_name == INGEST_QUEUE_NAME

    async def test_trigger_targets_ingest_queue(self, client, seeded_users):
        name = f"arq-qn-trigger-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        app.state.arq_pool.enqueue_job = AsyncMock()
        r = await client.post(
            f"/admin/sources/{source_id}/ingest",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        _, kwargs = app.state.arq_pool.enqueue_job.await_args
        assert kwargs.get("_queue_name") == INGEST_QUEUE_NAME

    async def test_resume_targets_ingest_queue(self, client, seeded_users, db_session):
        name = f"arq-qn-resume-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(), source_name=name, status="running",
            files_processed=0, files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        app.state.arq_pool.enqueue_job = AsyncMock()
        r = await client.post(
            f"/admin/sources/{source_id}/resume",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        _, kwargs = app.state.arq_pool.enqueue_job.await_args
        assert kwargs.get("_queue_name") == INGEST_QUEUE_NAME

        from sqlalchemy import delete
        await db_session.execute(delete(IngestRun).where(IngestRun.source_name == name))
        await db_session.commit()
