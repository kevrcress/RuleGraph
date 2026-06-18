"""Integration tests for Anthropic Batches re-attach on resume (Phase 4, decision #6).

Drives the BATCH path of batch_ingest_files with a fully MOCKED Anthropic client
(no real API calls). Verifies:
  * normal (non-resume) run calls batches.create exactly once and persists
    batch_id / batch_submitted_at / batch_status on the IngestRun.
  * a resume whose stored batch_id is still in-flight (batch_status != "ended")
    calls batches.create ZERO times and re-attaches via batches.retrieve instead
    (avoids double spend).
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.ingest import batch_pipeline
from app.models.ingest import IngestRun

# A single business-logic file so the batch path has one request to submit.
_FILES = [
    {"path": "src/orders/service.py", "content": "def authorize(order):\n    if order.total > 100:\n        return True\n"},
]


def _make_mock_client(*, created_batch, retrieved_batch, results):
    """Build a mock Anthropic client exposing messages.batches.{create,retrieve,results}."""
    batches = MagicMock()
    batches.create = AsyncMock(return_value=created_batch)
    batches.retrieve = AsyncMock(return_value=retrieved_batch)

    async def _results_aiter(_batch_id):
        for r in results:
            yield r

    batches.results = AsyncMock(side_effect=_results_aiter)

    client = MagicMock()
    client.messages.batches = batches
    return client


def _ended_batch(batch_id="batch_test_1"):
    return SimpleNamespace(id=batch_id, processing_status="ended")


def _errored_result(custom_id="file_0"):
    # Use an "errored" result so we never touch extraction/storage internals —
    # this test is about create-vs-retrieve call counts, not rule parsing.
    return SimpleNamespace(
        custom_id=custom_id,
        result=SimpleNamespace(type="errored", error="forced batch error (test)"),
    )


def _batch_settings_patches():
    return [
        patch("app.services.settings_service.is_claude_enabled", AsyncMock(return_value=True)),
        patch("app.services.settings_service.get_complexity_threshold", AsyncMock(return_value=0.5)),
        # No proxy URL -> the BATCH path runs (not the sequential/proxy path).
        patch("app.services.settings_service.get_litellm_base_url", AsyncMock(return_value=None)),
        patch("app.services.settings_service.get_anthropic_api_key", AsyncMock(return_value="x")),
        patch.object(batch_pipeline, "add_to_graph", AsyncMock(return_value="cognee-node-1")),
        patch("app.services.conflict_service.detect_and_store", AsyncMock(return_value=[])),
        patch("app.services.terminology_service.scan_content_and_update", AsyncMock(return_value=None)),
        patch("app.ingest.wiki_generator.generate_wiki_for_modules", AsyncMock(return_value=None)),
    ]


async def _cleanup_errors(db, source_name):
    """Remove IngestError rows this test creates (session-scoped shared DB)."""
    from sqlalchemy import delete
    from app.models.ingest import IngestError
    run_ids = (await db.execute(
        select(IngestRun.id).where(IngestRun.source_name == source_name)
    )).scalars().all()
    if run_ids:
        await db.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
        await db.commit()


class TestBatchReattach:

    async def test_normal_run_calls_create_once(self, db_session):
        db = db_session
        source_name = f"batch-create-{uuid.uuid4().hex[:8]}"

        created = _ended_batch("batch_normal_1")
        client = _make_mock_client(
            created_batch=created,
            retrieved_batch=created,
            results=[_errored_result("file_0")],
        )

        patches = _batch_settings_patches() + [
            patch.object(batch_pipeline, "_get_client", MagicMock(return_value=client)),
        ]
        for p in patches:
            p.start()
        try:
            await batch_pipeline.batch_ingest_files(db, _FILES, source_name)
        finally:
            for p in patches:
                p.stop()

        # create called exactly once; no re-attach retrieve before create.
        assert client.messages.batches.create.await_count == 1, "normal run must call create exactly once"

        # batch_id / status persisted on the run.
        run = (await db.execute(
            select(IngestRun).where(IngestRun.source_name == source_name).order_by(IngestRun.started_at.desc())
        )).scalars().first()
        assert run is not None
        assert run.batch_id == "batch_normal_1"
        assert run.batch_status == "ended"
        assert run.batch_submitted_at is not None

        await _cleanup_errors(db, source_name)

    async def test_resume_inflight_skips_create_and_reattaches(self, db_session):
        db = db_session
        source_name = f"batch-resume-{uuid.uuid4().hex[:8]}"

        # A prior run that submitted a batch still in flight (status != "ended").
        prior = IngestRun(
            id=uuid.uuid4(),
            source_name=source_name,
            status="running",
            files_processed=0,
            files_errored=0,
            batch_id="batch_inflight_9",
            batch_status="in_progress",
        )
        db.add(prior)
        await db.commit()

        # retrieve returns an ENDED batch so we fall straight through to results.
        retrieved = _ended_batch("batch_inflight_9")
        client = _make_mock_client(
            created_batch=_ended_batch("SHOULD_NOT_BE_USED"),
            retrieved_batch=retrieved,
            results=[_errored_result("file_0")],
        )

        patches = _batch_settings_patches() + [
            patch.object(batch_pipeline, "_get_client", MagicMock(return_value=client)),
        ]
        for p in patches:
            p.start()
        try:
            await batch_pipeline.batch_ingest_files(
                db, _FILES, source_name, resume_run=prior,
            )
        finally:
            for p in patches:
                p.stop()

        # GUARD: create must NOT be called when re-attaching to an in-flight batch.
        assert client.messages.batches.create.await_count == 0, "resume must NOT call create (double spend)"
        # retrieve must be used to re-attach.
        client.messages.batches.retrieve.assert_awaited_with("batch_inflight_9")
        assert client.messages.batches.retrieve.await_count >= 1

        await _cleanup_errors(db, source_name)
