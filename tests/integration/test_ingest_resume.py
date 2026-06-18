"""Integration tests for explicit admin Resume (Phase 5).

Covers two layers:
  * batch_ingest_files(resume=True, resume_run=...) — after a mid-run crash leaves
    some files unchecked, a resume processes ONLY the not-yet-done files, the union
    of checkpoints is correct, and no duplicate Rule rows are created.
  * POST /admin/sources/{id}/resume — 409 when nothing is resumable, and enqueues a
    background task when an incomplete run exists.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import delete, func, select

from app.ingest import batch_pipeline
from app.ingest.extractor import ExtractionResult, ExtractedRule
from app.models.ingest import IngestError, IngestFileCheckpoint, IngestRun
from app.models.rule import Rule
from app.services import ingest_service

# Three business-logic files. On the first (crashed) pass only the first file
# is processed; resume must handle the remaining two.
_F1 = "src/a/one.py"
_F2 = "src/b/two.py"
_F3 = "src/c/three.py"

_FILES = [
    {"path": _F1, "content": "def one(order):\n    if order.total > 1:\n        return True\n"},
    {"path": _F2, "content": "def two(order):\n    if order.total > 2:\n        return True\n"},
    {"path": _F3, "content": "def three(order):\n    if order.total > 3:\n        return True\n"},
]


def _result_for(content):
    title = f"Rule {content.split('(')[0].split()[-1]}"
    return ExtractionResult(
        rules=[ExtractedRule(title=title, definition=f"{title} definition.", confidence=0.9)],
        model_used="mock",
        summary="summary",
    )


def _seq_patches():
    return [
        patch("app.services.settings_service.is_claude_enabled", AsyncMock(return_value=True)),
        patch("app.services.settings_service.get_complexity_threshold", AsyncMock(return_value=0.5)),
        patch("app.services.settings_service.get_litellm_base_url", AsyncMock(return_value="http://proxy.local")),
        patch("app.services.settings_service.get_anthropic_api_key", AsyncMock(return_value="x")),
        patch.object(batch_pipeline, "add_to_graph", AsyncMock(return_value="cognee-node")),
        patch("app.services.conflict_service.detect_and_store", AsyncMock(return_value=[])),
        patch("app.services.terminology_service.scan_content_and_update", AsyncMock(return_value=None)),
        patch("app.ingest.wiki_generator.generate_wiki_for_modules", AsyncMock(return_value=None)),
    ]


async def _cleanup(db, source_name):
    run_ids = (await db.execute(
        select(IngestRun.id).where(IngestRun.source_name == source_name)
    )).scalars().all()
    if run_ids:
        await db.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
        await db.commit()


class TestIngestResume:

    async def test_resume_processes_only_remaining_files(self, db_session):
        db = db_session
        source_name = f"resume-test-{uuid.uuid4().hex[:8]}"

        # ── Pass 1: simulate a crash after the first file ──────────────────────
        # extract_rules raises on the 2nd file so the run aborts mid-way with only
        # _F1 checkpointed "done".
        call_state = {"n": 0}

        def crash_after_first(content, complexity, db_arg):
            call_state["n"] += 1
            if call_state["n"] >= 2:
                raise RuntimeError("simulated crash")
            return _result_for(content)

        patches = _seq_patches() + [
            patch.object(batch_pipeline, "extract_rules", AsyncMock(side_effect=crash_after_first)),
        ]
        for p in patches:
            p.start()
        try:
            await batch_pipeline.batch_ingest_files(db, _FILES, source_name)
        finally:
            for p in patches:
                p.stop()

        run = (await db.execute(
            select(IngestRun).where(IngestRun.source_name == source_name).order_by(IngestRun.started_at.desc())
        )).scalars().first()
        assert run is not None
        done_after_crash = await ingest_service.get_done_files(db, run.id)
        assert done_after_crash == {_F1}, f"expected only {_F1} done, got {done_after_crash}"

        rule_count_after_crash = (await db.execute(select(func.count(Rule.id)))).scalar_one()

        # ── Pass 2: resume — only _F2 and _F3 should be processed ──────────────
        processed_paths: list[str] = []

        def record(content, complexity, db_arg):
            processed_paths.append(content)
            return _result_for(content)

        patches2 = _seq_patches() + [
            patch.object(batch_pipeline, "extract_rules", AsyncMock(side_effect=record)),
        ]
        for p in patches2:
            p.start()
        try:
            summary = await batch_pipeline.batch_ingest_files(
                db, _FILES, source_name, resume_run=run, resume=True,
            )
        finally:
            for p in patches2:
                p.stop()

        # Only the two not-yet-done files were extracted on resume.
        assert len(processed_paths) == 2, f"resume must process only remaining files, got {len(processed_paths)}"
        assert all("one(" not in c for c in processed_paths), "already-done file must NOT be reprocessed"

        # Union of checkpoints: all three files now done on the SAME run.
        done_after_resume = await ingest_service.get_done_files(db, run.id)
        assert done_after_resume == {_F1, _F2, _F3}, f"all files should be done, got {done_after_resume}"
        assert summary["files_processed"] == 2

        # No duplicate Rule rows: each file contributes exactly one rule, three total.
        rule_count_after_resume = (await db.execute(select(func.count(Rule.id)))).scalar_one()
        assert rule_count_after_resume == rule_count_after_crash + 2, (
            f"resume added unexpected Rule rows: {rule_count_after_crash} -> {rule_count_after_resume}"
        )

        await _cleanup(db, source_name)

    async def test_resume_all_done_marks_complete_and_no_submit(self, db_session):
        db = db_session
        source_name = f"resume-alldone-{uuid.uuid4().hex[:8]}"

        # A run with every file already checkpointed done.
        run = await ingest_service.start_run(db, source_name)
        await db.commit()
        for f in _FILES:
            await ingest_service.mark_file_checkpoint(db, run.id, f["path"], "done")
        await db.commit()

        extract_mock = AsyncMock(side_effect=lambda content, c, d: _result_for(content))
        patches = _seq_patches() + [
            patch.object(batch_pipeline, "extract_rules", extract_mock),
        ]
        for p in patches:
            p.start()
        try:
            summary = await batch_pipeline.batch_ingest_files(
                db, _FILES, source_name, resume_run=run, resume=True,
            )
        finally:
            for p in patches:
                p.stop()

        assert extract_mock.await_count == 0, "no file should be processed when all are already done"
        assert summary["files_processed"] == 0
        await db.refresh(run)
        assert run.status == "completed"

        await _cleanup(db, source_name)


class TestResumeRoute:

    async def _create_source(self, client, seeded_users, name):
        r = await client.post(
            "/admin/sources",
            json={"name": name, "source_type": "github_repo", "repo_url": "https://example.com/r.git", "branch": "main"},
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    async def test_resume_returns_409_when_nothing_resumable(self, client, seeded_users):
        name = f"resume-route-none-{uuid.uuid4().hex[:8]}"
        source_id = await self._create_source(client, seeded_users, name)

        # No ingest run exists for this fresh source → not resumable.
        r = await client.post(
            f"/admin/sources/{source_id}/resume",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 409, r.text

    async def test_resume_enqueues_when_incomplete_run_exists(self, client, seeded_users, db_session):
        name = f"resume-route-ok-{uuid.uuid4().hex[:8]}"
        source_id = await self._create_source(client, seeded_users, name)

        # Seed an incomplete (status="running") run linked by source_name.
        run = IngestRun(
            id=uuid.uuid4(), source_name=name, status="running",
            files_processed=0, files_errored=0,
        )
        db_session.add(run)
        await db_session.commit()

        # The route enqueues an arq job instead of running inline. Assert on the
        # mocked pool's enqueue_job (set on app.state.arq_pool in conftest).
        from app.main import app
        app.state.arq_pool.enqueue_job = AsyncMock()
        r = await client.post(
            f"/admin/sources/{source_id}/resume",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "resumed"
        from app.tasks.worker import INGEST_QUEUE_NAME
        app.state.arq_pool.enqueue_job.assert_awaited_once_with(
            "run_source_ingest", str(source_id), True, _queue_name=INGEST_QUEUE_NAME
        )

        await db_session.execute(delete(IngestRun).where(IngestRun.source_name == name))
        await db_session.commit()

    async def _delete_run(self, db_session, name):
        run_ids = (await db_session.execute(
            select(IngestRun.id).where(IngestRun.source_name == name)
        )).scalars().all()
        if run_ids:
            await db_session.execute(
                delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id.in_(run_ids))
            )
            await db_session.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
            await db_session.commit()

    async def test_resume_requires_admin(self, client, seeded_users):
        name = f"resume-route-auth-{uuid.uuid4().hex[:8]}"
        source_id = await self._create_source(client, seeded_users, name)
        r = await client.post(
            f"/admin/sources/{source_id}/resume",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
        )
        assert r.status_code in (401, 403), r.text

    async def test_list_sources_surfaces_run_progress(self, client, seeded_users, db_session):
        """GET /admin/sources (the LIST route) must populate run_status/done/total
        for a source that has an ingest run with checkpoints (DR-202 fix)."""
        name = f"resume-list-progress-{uuid.uuid4().hex[:8]}"
        source_id = await self._create_source(client, seeded_users, name)

        # Seed an incomplete run (matched to the source by source_name == name) with
        # two checkpoints: one done, one error. Expect run_status="running",
        # done_file_count=1, total_file_count=2 on the list payload.
        run = await ingest_service.start_run(db_session, name)
        await db_session.commit()
        await ingest_service.mark_file_checkpoint(db_session, run.id, _F1, "done")
        await ingest_service.mark_file_checkpoint(db_session, run.id, _F2, "error", "boom")
        await db_session.commit()

        r = await client.get(
            "/admin/sources",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"},
        )
        assert r.status_code == 200, r.text
        item = next((i for i in r.json()["items"] if i["id"] == source_id), None)
        assert item is not None, "created source missing from list response"
        assert item["run_status"] == "running", item
        assert item["done_file_count"] == 1, item
        assert item["total_file_count"] == 2, item

        await self._delete_run(db_session, name)
