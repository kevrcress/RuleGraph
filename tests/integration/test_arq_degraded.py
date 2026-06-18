"""Guard tests for Phase 4 — degraded-mode 503 when the arq pool is unavailable.

When Redis is down at boot, `app/main.py` leaves `app.state.arq_pool` as None.
The three ingest enqueue routes must return a clear 503 ("Ingest queue
unavailable …") instead of an opaque 500 caused by `None.enqueue_job` raising
AttributeError.

Each test sets `app.state.arq_pool = None`, exercises a route, and restores the
mock pool in a finally block — the `client` fixture is session-scoped, so leaving
the pool as None would break every later enqueue test.
"""
import uuid

from app.main import app
from app.models.ingest import IngestRun

_EXPECTED_DETAIL = "Ingest queue unavailable — background worker/Redis not reachable"


async def _create_source(client, seeded_users, name):
    r = await client.post(
        "/admin/sources",
        json={"name": name, "source_type": "github_repo", "repo_url": "https://example.com/r.git", "branch": "main"},
        headers={"Authorization": f"Bearer {seeded_users['admin']}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestDegradedModePool:

    async def test_trigger_returns_503_when_pool_none(self, client, seeded_users):
        name = f"degraded-trigger-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        saved = app.state.arq_pool
        app.state.arq_pool = None
        try:
            r = await client.post(
                f"/admin/sources/{source_id}/ingest",
                headers={"Authorization": f"Bearer {seeded_users['admin']}"},
            )
        finally:
            app.state.arq_pool = saved

        assert r.status_code == 503, r.text
        assert r.json()["detail"] == _EXPECTED_DETAIL

    async def test_resume_returns_503_when_pool_none(self, client, seeded_users, db_session):
        name = f"degraded-resume-{uuid.uuid4().hex[:8]}"
        source_id = await _create_source(client, seeded_users, name)

        run = IngestRun(
            id=uuid.uuid4(), source_name=name, status="running",
            files_processed=0, files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        saved = app.state.arq_pool
        app.state.arq_pool = None
        try:
            r = await client.post(
                f"/admin/sources/{source_id}/resume",
                headers={"Authorization": f"Bearer {seeded_users['admin']}"},
            )
        finally:
            app.state.arq_pool = saved

        assert r.status_code == 503, r.text
        assert r.json()["detail"] == _EXPECTED_DETAIL

        from sqlalchemy import delete
        await db_session.execute(delete(IngestRun).where(IngestRun.source_name == name))
        await db_session.commit()

    async def test_ingest_all_returns_503_when_pool_none(self, client, seeded_users):
        # An active source must exist so the route reaches the pool guard rather
        # than the "no_sources_configured" early return.
        name = f"degraded-all-{uuid.uuid4().hex[:8]}"
        await _create_source(client, seeded_users, name)

        saved = app.state.arq_pool
        app.state.arq_pool = None
        try:
            r = await client.post(
                "/ingest",
                headers={"Authorization": f"Bearer {seeded_users['admin']}"},
            )
        finally:
            app.state.arq_pool = saved

        assert r.status_code == 503, r.text
        assert r.json()["detail"] == _EXPECTED_DETAIL
