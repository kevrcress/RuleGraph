"""Integration tests for per-file ingest checkpoints (Phase 3).

Drives the SEQUENTIAL path of batch_ingest_files directly against the test DB,
forcing one file to fail extraction. Verifies:
  * one "done" checkpoint and one "error" checkpoint row exist for the run
  * a second run over the same files adds zero new Rule rows (store_rule upsert
    idempotency) — duplicate Cognee nodes are acceptable per DEC-001.
"""
import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select

from app.ingest import batch_pipeline
from app.ingest.extractor import ExtractionResult, ExtractedRule
from app.models.ingest import IngestFileCheckpoint
from app.models.rule import Rule

# Two files: one extracts cleanly, one returns an extraction error.
_GOOD_PATH = "src/good/service.py"
_BAD_PATH = "src/bad/broken.py"

_FILES = [
    {"path": _GOOD_PATH, "content": "def authorize(order):\n    if order.total > 100:\n        return True\n"},
    {"path": _BAD_PATH, "content": "def cancel(order):\n    return order.age < 30\n"},
]

_GOOD_RESULT = ExtractionResult(
    rules=[ExtractedRule(title="Authorize Large Orders", definition="Orders over 100 are authorized.", confidence=0.9)],
    model_used="mock",
    summary="Authorization logic.",
)
_BAD_RESULT = ExtractionResult(rules=[], model_used="mock", error="forced extraction failure")


def _extract_side_effect(content, complexity, db):
    # The bad file's content is unique enough to key on.
    if "cancel" in content:
        return _BAD_RESULT
    return _GOOD_RESULT


async def _checkpoint_counts(db, run_id):
    rows = (await db.execute(
        select(IngestFileCheckpoint.status, IngestFileCheckpoint.file_path)
        .where(IngestFileCheckpoint.ingest_run_id == run_id)
    )).all()
    return rows


class TestIngestCheckpoints:

    async def test_sequential_checkpoints_and_idempotency(self, db_session):
        db = db_session
        source_name = f"checkpoint-test-{uuid.uuid4().hex[:8]}"

        # Force the sequential (proxy) path and stub out all network calls.
        patches = [
            patch("app.services.settings_service.is_claude_enabled", AsyncMock(return_value=True)),
            patch("app.services.settings_service.get_complexity_threshold", AsyncMock(return_value=0.5)),
            patch("app.services.settings_service.get_litellm_base_url", AsyncMock(return_value="http://proxy.local")),
            patch("app.services.settings_service.get_anthropic_api_key", AsyncMock(return_value="x")),
            patch.object(batch_pipeline, "extract_rules", AsyncMock(side_effect=_extract_side_effect)),
            patch.object(batch_pipeline, "add_to_graph", AsyncMock(return_value="cognee-node-1")),
            patch("app.services.conflict_service.detect_and_store", AsyncMock(return_value=[])),
            patch("app.services.terminology_service.scan_content_and_update", AsyncMock(return_value=None)),
            patch("app.ingest.wiki_generator.generate_wiki_for_modules", AsyncMock(return_value=None)),
        ]
        for p in patches:
            p.start()
        try:
            result1 = await batch_pipeline.batch_ingest_files(db, _FILES, source_name)
        finally:
            for p in patches:
                p.stop()

        # Find the run this call created (most recent for this source).
        from app.models.ingest import IngestRun
        run_id = (await db.execute(
            select(IngestRun.id).where(IngestRun.source_name == source_name).order_by(IngestRun.started_at.desc())
        )).scalars().first()
        assert run_id is not None, "ingest run was not created"

        rows = await _checkpoint_counts(db, run_id)
        statuses = {path: status for status, path in rows}
        assert statuses.get(_GOOD_PATH) == "done", f"expected done checkpoint for good file, got {rows}"
        assert statuses.get(_BAD_PATH) == "error", f"expected error checkpoint for bad file, got {rows}"
        assert len([r for r in rows if r[0] == "done"]) == 1
        assert len([r for r in rows if r[0] == "error"]) == 1

        # One rule from the good file only.
        assert result1["rules_extracted"] == 1

        rule_count_after_first = (await db.execute(select(func.count(Rule.id)))).scalar_one()

        # Second run over the same files: store_rule upsert must add zero new Rule rows.
        patches2 = [
            patch("app.services.settings_service.is_claude_enabled", AsyncMock(return_value=True)),
            patch("app.services.settings_service.get_complexity_threshold", AsyncMock(return_value=0.5)),
            patch("app.services.settings_service.get_litellm_base_url", AsyncMock(return_value="http://proxy.local")),
            patch("app.services.settings_service.get_anthropic_api_key", AsyncMock(return_value="x")),
            patch.object(batch_pipeline, "extract_rules", AsyncMock(side_effect=_extract_side_effect)),
            patch.object(batch_pipeline, "add_to_graph", AsyncMock(return_value="cognee-node-2")),
            patch("app.services.conflict_service.detect_and_store", AsyncMock(return_value=[])),
            patch("app.services.terminology_service.scan_content_and_update", AsyncMock(return_value=None)),
            patch("app.ingest.wiki_generator.generate_wiki_for_modules", AsyncMock(return_value=None)),
        ]
        for p in patches2:
            p.start()
        try:
            await batch_pipeline.batch_ingest_files(db, _FILES, source_name)
        finally:
            for p in patches2:
                p.stop()

        rule_count_after_second = (await db.execute(select(func.count(Rule.id)))).scalar_one()
        assert rule_count_after_second == rule_count_after_first, (
            f"second run created new Rule rows: {rule_count_after_first} -> {rule_count_after_second}"
        )

        # Clean up the IngestError rows this test intentionally created — the DB
        # session is session-scoped and shared, and the admin /ingest-errors
        # endpoint lists errors globally (test_clean_seed_produces_no_errors
        # asserts an empty list). Scope the delete to this source's runs only.
        from sqlalchemy import delete
        from app.models.ingest import IngestError, IngestRun
        run_ids = (await db.execute(
            select(IngestRun.id).where(IngestRun.source_name == source_name)
        )).scalars().all()
        if run_ids:
            await db.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
            await db.commit()
