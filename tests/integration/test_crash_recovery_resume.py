"""Integration test for the full crash → recovery → resume state machine (Phase 6).

This is the ONE focused test that ties the two halves of worker-crash recovery
together in-process:

  1. A worker crash leaves a source pinned at ``ingest_status="ingesting"`` with a
     STALE ``IngestRun`` and PARTIAL ``IngestFileCheckpoint`` rows (one file done,
     two not). Nothing else flips it back.
  2. ``reset_stale_ingests`` (the cron/startup sweep, ``app/tasks/recovery.py``)
     recovers it: the source goes to ``error`` and the run becomes resumable
     (``running`` → ``completed_with_errors``).
  3. The resume path (``batch_ingest_files(resume=True, resume_run=...)``) then
     reprocesses ONLY the not-yet-done files — no duplicate work on the already
     checkpointed file, and no duplicate ``Rule`` rows.

A true cross-process "kill the worker, watch the arq cron recover it" run is NOT
assertable by the suite (it needs a live worker + Redis cron tick). That single
step is documented as a MANUAL smoke test in the changes log; the manual command
is ``arq app.tasks.worker.WorkerSettings``. Everything else — the recovery state
machine and the resume skip logic — is exercised in-process here.

Teardown deletes checkpoint rows before run rows (the checkpoints FK has no
ON DELETE CASCADE), then the source.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import delete, func, select

from app.config import settings
from app.ingest import batch_pipeline
from app.ingest.extractor import ExtractedRule, ExtractionResult
from app.models.ingest import IngestError, IngestFileCheckpoint, IngestRun
from app.models.ingest_source import IngestSource
from app.models.rule import Rule
from app.services import ingest_service
from app.tasks.recovery import reset_stale_ingests

# Three business-logic files. The crashed run checkpointed only _F1 "done";
# recovery + resume must reprocess only _F2 and _F3.
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


class TestCrashRecoveryResume:

    async def test_stale_recovery_then_resume_processes_only_undone_files(self, db_session):
        db = db_session
        suffix = uuid.uuid4().hex[:8]
        source_name = f"crash-recover-{suffix}"

        # Beyond timeout + grace so the run is unambiguously stale.
        far_past = datetime.now(timezone.utc) - timedelta(
            seconds=settings.ingest_job_timeout_seconds + 10_000
        )

        # ── Seed the post-crash state ──────────────────────────────────────────
        # Source pinned at "ingesting"; a "running" run started long ago; ONE file
        # (_F1) checkpointed "done" with an old processed_at (no recent progress).
        src = IngestSource(
            id=uuid.uuid4(),
            name=source_name,
            source_type="github_repo",
            repo_url="https://example.com/r.git",
            branch="main",
            ingest_status="ingesting",
        )
        db.add(src)
        run = IngestRun(
            id=uuid.uuid4(), source_name=source_name, status="running",
            started_at=far_past, files_processed=1, files_errored=0,
        )
        db.add(run)
        await db.flush()
        db.add(IngestFileCheckpoint(
            id=uuid.uuid4(), ingest_run_id=run.id, file_path=_F1,
            status="done", processed_at=far_past,
        ))
        await db.commit()

        try:
            # ── Step A: recovery sweep flips the stale source and makes the run resumable ──
            reset = await reset_stale_ingests(db)
            assert reset == [source_name], f"expected only {source_name} recovered, got {reset}"

            await db.refresh(src)
            await db.refresh(run)
            assert src.ingest_status == "error", "stale source must be flipped to error"
            assert run.status == "completed_with_errors", "run must be made resumable"

            # The partial checkpoint survives recovery — _F1 is still done.
            done_after_recovery = await ingest_service.get_done_files(db, run.id)
            assert done_after_recovery == {_F1}, f"expected only {_F1} done, got {done_after_recovery}"

            rule_count_before_resume = (await db.execute(select(func.count(Rule.id)))).scalar_one()

            # ── Step B: resume — only the two undone files (_F2, _F3) reprocess ──
            processed: list[str] = []

            def record(content, complexity, db_arg):
                processed.append(content)
                return _result_for(content)

            patches = _seq_patches() + [
                patch.object(batch_pipeline, "extract_rules", AsyncMock(side_effect=record)),
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

            # Only the not-yet-done files were extracted on resume; _F1 was NOT.
            assert len(processed) == 2, f"resume must process only undone files, got {len(processed)}"
            assert all("one(" not in c for c in processed), "already-done file must NOT be reprocessed"
            assert summary["files_processed"] == 2

            # All three files now done on the SAME run (checkpoint union).
            done_after_resume = await ingest_service.get_done_files(db, run.id)
            assert done_after_resume == {_F1, _F2, _F3}, f"all files should be done, got {done_after_resume}"

            # No duplicate Rule rows: resume adds exactly two (one per undone file).
            rule_count_after_resume = (await db.execute(select(func.count(Rule.id)))).scalar_one()
            assert rule_count_after_resume == rule_count_before_resume + 2, (
                f"resume added unexpected Rule rows: {rule_count_before_resume} -> {rule_count_after_resume}"
            )
        finally:
            run_ids = (await db.execute(
                select(IngestRun.id).where(IngestRun.source_name == source_name)
            )).scalars().all()
            if run_ids:
                await db.execute(delete(IngestError).where(IngestError.ingest_run_id.in_(run_ids)))
                await db.execute(
                    delete(IngestFileCheckpoint).where(IngestFileCheckpoint.ingest_run_id.in_(run_ids))
                )
                await db.execute(delete(IngestRun).where(IngestRun.id.in_(run_ids)))
            await db.execute(delete(IngestSource).where(IngestSource.name == source_name))
            await db.commit()
