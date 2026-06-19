"""
Batch ingest pipeline — submits repo files to Anthropic Messages Batches API,
or falls back to sequential processing when a LiteLLM proxy is configured.

Uses the Batches API (50% cost reduction vs. real-time) for repo ingestion when
calling Anthropic directly. When LITELLM_BASE_URL / litellm_base_url is set,
the Batches endpoint is unavailable so files are processed one at a time via
the regular messages.create() path (same quality, higher per-token cost).

Single-file uploads always use process_file() from pipeline.py.

Flow (Anthropic / batch mode):
  1. Score all files with score_complexity(); skip 0.0 files
  2. Read complexity threshold from DB admin settings
  3. Build batch requests (Haiku or Sonnet based on threshold, content truncated)
  4. Submit to Anthropic Batches API
  5. Poll every 30s until processing_status == "ended"
  6. For each succeeded result: parse rules → store → Cognee → flush
  7. Run conflict detection and terminology scan once at the end

Flow (proxy / sequential mode):
  1–2. Same scoring and threshold
  3. Call extract_rules() per file (which commits before each LLM call)
  4–7. Same per-file storage → end-of-batch post-processing
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.complexity import score_complexity
from app.ingest.extractor import (
    _get_client,
    build_batch_request,
    extract_rules,
    _parse_llm_response,
    ExtractedRule,
)
from app.graph.cognee_client import add_to_graph
from app.models.ingest import IngestRun
from app.services import ingest_service

logger = logging.getLogger(__name__)

_SKIP_SEGMENTS = frozenset({
    "src", "source", "lib", "libs", "app", "main",
    "packages", "core", "internal", "test", "tests",
    "spec", "specs", "__tests__",
})


def derive_module_from_path(file_path: str, repo_name: str) -> str:
    """
    Derive a module/domain label from a file path for service grouping.

    src/payments/service.ts       -> "{repo_name}/payments"
    packages/orders/src/model.ts  -> "{repo_name}/orders"
    utils.py                      -> "{repo_name}"

    This gives the wiki generator natural per-domain groupings instead of
    lumping every file from a repo into a single flat service entry.
    """
    parts = Path(file_path).parts
    for part in parts[:-1]:  # exclude the filename itself
        if part.lower() not in _SKIP_SEGMENTS and not part.startswith("."):
            return f"{repo_name}/{part}"
    return repo_name

_POLL_INTERVAL = 30       # seconds between status checks


def _max_polls() -> int:
    """Batch poll budget in poll-iterations, derived from config so it stays reconciled.

    budget = (job_timeout − reserve) // interval, kept strictly below the arq
    job_timeout (reserve covers clone + scoring + results streaming) so the poll
    loop raises its own TimeoutError and flushes checkpoints before arq kills the
    worker mid-write. See DEC-045 for the full timing model.
    """
    from app.config import settings
    budget = settings.ingest_job_timeout_seconds - settings.ingest_batch_poll_reserve_seconds
    return max(1, budget // _POLL_INTERVAL)


async def _finalize_empty_resume(db: AsyncSession, run: IngestRun, last_file: str | None) -> None:
    """Mark an existing run complete when a resume finds no remaining files to process.

    Counts the run's existing done/error checkpoints so the run's tallies reflect the
    work already performed by the prior (crashed) attempt rather than zeroing them out.
    """
    done_count, errored_count = await ingest_service.count_checkpoint_tallies(db, run.id)
    await ingest_service.complete_run(
        db, run.id,
        status="completed" if errored_count == 0 else "completed_with_errors",
        files_processed=done_count,
        files_errored=errored_count,
        last_processed_file=last_file,
    )
    await db.commit()


async def batch_ingest_files(
    db: AsyncSession,
    files: list[dict],
    source_name: str,
    src=None,
    resume_run: IngestRun | None = None,
    resume: bool = False,
) -> dict:
    """
    Ingest a list of files using the Anthropic Batches API (direct) or sequential
    messages.create() calls (when a LiteLLM proxy URL is configured).

    Args:
        db: Active database session.
        files: List of {"path": str, "content": str} dicts from the repo connector.
        source_name: Service/source label (used for rule association and run tracking).

    Returns:
        Summary dict: rules_extracted, files_processed, files_skipped, errors.
    """
    async def _set_progress(msg: str) -> None:
        if src is not None:
            src.ingest_progress = msg
            await db.commit()

    from app.services.settings_service import (
        is_claude_enabled, get_complexity_threshold,
        get_anthropic_api_key, get_litellm_base_url,
        get_llm_request_timeout,
    )

    if not await is_claude_enabled(db):
        logger.info("Claude API disabled — skipping batch ingest for '%s'", source_name)
        return {
            "rules_extracted": 0,
            "files_processed": 0,
            "files_skipped": len(files),
            "errors": ["Claude API is disabled by admin"],
        }

    threshold = await get_complexity_threshold(db)
    base_url = await get_litellm_base_url(db)

    # Score files and build request map
    requests_map: dict[str, dict] = {}   # custom_id → {path, content, complexity}

    for i, file_info in enumerate(files):
        complexity = score_complexity(file_info["content"])
        if complexity == 0.0:
            logger.debug("Skipping '%s' — complexity 0.0", file_info["path"])
            continue
        requests_map[f"file_{i}"] = {**file_info, "complexity": complexity}

    files_skipped = len(files) - len(requests_map)

    if not requests_map:
        logger.info("No files with business logic found for source '%s'", source_name)
        return {"rules_extracted": 0, "files_processed": 0, "files_skipped": files_skipped, "errors": []}

    # Close the settings read transaction before any long-running operation so the
    # 30s idle_in_transaction_session_timeout doesn't kill the connection.
    await db.commit()

    rules_extracted = 0
    files_processed = 0
    files_errored = 0
    errors: list[str] = []
    last_file: str | None = None
    service_cache: dict[str, object] = {}
    module_file_summaries: dict[str, list[str]] = {}

    if base_url:
        # Sequential path: LiteLLM proxy does not implement /v1/messages/batches
        await _set_progress(
            f"Scoring complete — processing {len(requests_map)} file(s) via proxy…"
        )
        logger.info(
            "Proxy configured — processing %d files sequentially for '%s'",
            len(requests_map), source_name,
        )

        if resume and resume_run is not None:
            run = resume_run
        else:
            run = await ingest_service.start_run(db, source_name)
            await db.commit()

        if resume:
            done = await ingest_service.get_done_files(db, run.id)
            requests_map = {cid: fi for cid, fi in requests_map.items() if fi["path"] not in done}
            if not requests_map:
                logger.info(
                    "Resume for '%s': all files already done — nothing to process", source_name
                )
                await _finalize_empty_resume(db, run, last_file=None)
                return {
                    "rules_extracted": 0,
                    "files_processed": 0,
                    "files_skipped": files_skipped,
                    "errors": [],
                }

        for custom_id, file_info in requests_map.items():
            filename = file_info["path"]
            last_file = filename
            await _set_progress(f"Processing {filename}…")

            try:
                result = await extract_rules(file_info["content"], file_info["complexity"], db)

                if result.error:
                    logger.error("Extraction error for '%s': %s", filename, result.error)
                    errors.append(f"{filename}: {result.error}")
                    files_errored += 1
                    await ingest_service.log_error(
                        db=db,
                        run_id=run.id,
                        source_name=source_name,
                        file_path=filename,
                        error_source="llm_extraction",
                        error_message=result.error,
                        raw_content=file_info["content"][:5000],
                    )
                    await ingest_service.mark_file_checkpoint(db, run.id, filename, "error", result.error)
                    await db.commit()
                    continue

                extracted = result.rules
                file_summary = result.summary
                logger.info("Parsed %d rules from '%s'", len(extracted), filename)

                cognee_node_id = await add_to_graph(file_info["content"], dataset_name="rulegraph", db=db)

                module = derive_module_from_path(filename, source_name)
                if module not in service_cache:
                    service_cache[module] = await ingest_service.get_or_create_service(db, module)
                    await db.commit()
                file_service = service_cache[module]

                if file_summary:
                    module_file_summaries.setdefault(module, []).append(file_summary)

                file_store_failed = False
                for rule in extracted:
                    try:
                        await ingest_service.store_rule(
                            db=db,
                            title=rule.title,
                            definition=rule.definition,
                            confidence=rule.confidence,
                            source_type="code",
                            cognee_node_id=cognee_node_id,
                            service_id=file_service.id,
                            source_file=filename,
                        )
                        rules_extracted += 1
                    except Exception as exc:
                        logger.error("Failed to store rule '%s': %s", rule.title, exc)
                        errors.append(str(exc))
                        file_store_failed = True

                # Only checkpoint "done" when the file's rules actually persisted. If any
                # store failed, checkpoint "error" so a Resume reprocesses the file (store_rule
                # is an idempotent upsert, so already-stored rules are not duplicated).
                if file_store_failed:
                    files_errored += 1
                    await ingest_service.mark_file_checkpoint(
                        db, run.id, filename, "error", "one or more rules failed to store"
                    )
                else:
                    files_processed += 1
                    await ingest_service.mark_file_checkpoint(db, run.id, filename, "done")
                await db.commit()

            except Exception as exc:
                logger.error("Unexpected error processing '%s': %s", filename, exc)
                errors.append(f"{filename}: {exc}")
                files_errored += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                # Write the error checkpoint in its OWN transaction so it survives
                # the rollback of the failed file's writes.
                try:
                    await ingest_service.mark_file_checkpoint(db, run.id, filename, "error", str(exc))
                    await db.commit()
                except Exception:
                    await db.rollback()

    else:
        # Batch API path (Anthropic only). Pass the configured request timeout so a
        # hung Batches control-plane call (create/retrieve/results) can't block the
        # worker indefinitely (matches the sequential path in extractor.extract_rules).
        _client = _get_client(
            await get_anthropic_api_key(db),
            timeout=await get_llm_request_timeout(db),
        )

        # Create the run BEFORE submitting so we can persist the Anthropic batch.id
        # immediately on submit (decision #6 — re-attach on resume to avoid double spend).
        # On resume, reuse the prior incomplete run so its done-file checkpoints apply
        # and new checkpoints attach to the same run.id.
        if resume and resume_run is not None:
            run = resume_run
        else:
            run = await ingest_service.start_run(db, source_name)
            await db.commit()

        if resume:
            done = await ingest_service.get_done_files(db, run.id)
            requests_map = {cid: fi for cid, fi in requests_map.items() if fi["path"] not in done}
            if not requests_map:
                logger.info(
                    "Resume for '%s': all files already done — nothing to submit", source_name
                )
                await _finalize_empty_resume(db, run, last_file=None)
                return {
                    "rules_extracted": 0,
                    "files_processed": 0,
                    "files_skipped": files_skipped,
                    "errors": [],
                }

        batch_requests = [
            build_batch_request(cid, fi["content"], fi["complexity"], threshold)
            for cid, fi in requests_map.items()
        ]

        # Resume guard: if a prior run handed us an in-flight batch_id, re-attach to it
        # instead of creating a new batch (avoids double spend). On retrieve failure or an
        # already-ended status, fall through to normal create/results handling.
        batch = None
        if resume_run is not None and resume_run.batch_id and resume_run.batch_status != "ended":
            try:
                batch = await _client.messages.batches.retrieve(resume_run.batch_id)
                run.batch_id = batch.id
                run.batch_submitted_at = resume_run.batch_submitted_at
                run.batch_status = batch.processing_status
                await db.commit()
                await _set_progress("Re-attached to in-flight AI batch — waiting for results…")
                logger.info(
                    "Re-attached to batch %s (status %s) for source '%s' — skipping create",
                    batch.id, batch.processing_status, source_name,
                )
            except Exception as exc:
                logger.warning(
                    "Re-attach to batch %s failed (%s) — submitting a fresh batch",
                    resume_run.batch_id, exc,
                )
                batch = None

        if batch is None:
            await _set_progress(f"Scoring complete — submitting {len(batch_requests)} file(s) to AI…")
            logger.info("Submitting batch of %d files for source '%s'", len(batch_requests), source_name)

            batch = await _client.messages.batches.create(requests=batch_requests)
            run.batch_id = batch.id
            run.batch_submitted_at = datetime.now(timezone.utc)
            run.batch_status = batch.processing_status
            await db.commit()
            await _set_progress(f"AI batch submitted ({len(batch_requests)} file(s)) — waiting for results…")
            logger.info("Batch %s submitted — polling every %ds for completion", batch.id, _POLL_INTERVAL)

        if batch.processing_status != "ended":
            max_polls = _max_polls()
            for poll_num in range(max_polls):
                await asyncio.sleep(_POLL_INTERVAL)
                batch = await _client.messages.batches.retrieve(batch.id)
                run.batch_status = batch.processing_status
                # Heartbeat: prove the run is alive during the checkpoint-free poll phase
                # so the staleness sweep doesn't reset a still-live batch (DEC-045).
                run.last_heartbeat_at = datetime.now(timezone.utc)
                await db.commit()
                elapsed_min = (poll_num + 1) * _POLL_INTERVAL // 60
                logger.debug("Batch %s status: %s (poll %d)", batch.id, batch.processing_status, poll_num + 1)
                if batch.processing_status == "ended":
                    break
                if elapsed_min > 0:
                    await _set_progress(f"AI processing… ({elapsed_min}m elapsed)")
            else:
                raise TimeoutError(
                    f"Batch {batch.id} did not complete within {max_polls * _POLL_INTERVAL}s"
                )

        await _set_progress("Processing AI results…")

        results_stream = await _client.messages.batches.results(batch.id)
        async for result in results_stream:
            file_info = requests_map.get(result.custom_id)
            if file_info is None:
                continue

            filename = file_info["path"]
            last_file = filename

            if result.result.type == "errored":
                error_msg = str(result.result.error)
                logger.error("Batch error for '%s': %s", filename, error_msg)
                errors.append(f"{filename}: {error_msg}")
                files_errored += 1
                await ingest_service.log_error(
                    db=db,
                    run_id=run.id,
                    source_name=source_name,
                    file_path=filename,
                    error_source="llm_extraction",
                    error_message=error_msg,
                    raw_content=file_info["content"][:5000],
                )
                await ingest_service.mark_file_checkpoint(db, run.id, filename, "error", error_msg)
                await db.commit()
                continue

            if result.result.type != "succeeded":
                await ingest_service.mark_file_checkpoint(
                    db, run.id, filename, "error", f"batch result type: {result.result.type}"
                )
                await db.commit()
                continue

            # Per-file isolation: an unexpected error (parse, Cognee, service lookup, store)
            # must not break out of the results stream and strand the remaining files. Mirror
            # the sequential path — mark the file "error" in its own transaction and continue.
            try:
                message = result.result.message
                response_text = message.content[0].text if message.content else ""
                raw_rules, file_summary = _parse_llm_response(response_text)

                extracted: list[ExtractedRule] = []
                for r in raw_rules:
                    title = r.get("title", "").strip()
                    definition = r.get("definition", "").strip()
                    if not title or not definition:
                        continue
                    confidence = max(0.0, min(1.0, float(r.get("confidence", 0.5))))
                    if confidence == 0.0:
                        continue
                    extracted.append(ExtractedRule(title=title, definition=definition, confidence=confidence))

                logger.info("Parsed %d rules from '%s'", len(extracted), filename)

                cognee_node_id = await add_to_graph(file_info["content"], dataset_name="rulegraph", db=db)

                module = derive_module_from_path(filename, source_name)
                if module not in service_cache:
                    service_cache[module] = await ingest_service.get_or_create_service(db, module)
                    await db.commit()
                file_service = service_cache[module]

                if file_summary:
                    module_file_summaries.setdefault(module, []).append(file_summary)

                file_store_failed = False
                for rule in extracted:
                    try:
                        await ingest_service.store_rule(
                            db=db,
                            title=rule.title,
                            definition=rule.definition,
                            confidence=rule.confidence,
                            source_type="code",
                            cognee_node_id=cognee_node_id,
                            service_id=file_service.id,
                            source_file=filename,
                        )
                        rules_extracted += 1
                    except Exception as exc:
                        logger.error("Failed to store rule '%s': %s", rule.title, exc)
                        errors.append(str(exc))
                        file_store_failed = True

                # Only checkpoint "done" when the file's rules actually persisted (see the
                # sequential path) so a Resume reprocesses any file whose stores failed.
                if file_store_failed:
                    files_errored += 1
                    await ingest_service.mark_file_checkpoint(
                        db, run.id, filename, "error", "one or more rules failed to store"
                    )
                else:
                    files_processed += 1
                    await ingest_service.mark_file_checkpoint(db, run.id, filename, "done")
                await db.commit()

            except Exception as exc:
                logger.error("Unexpected error processing batch result for '%s': %s", filename, exc)
                errors.append(f"{filename}: {exc}")
                files_errored += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                # Error checkpoint in its OWN transaction so it survives the rollback above.
                try:
                    await ingest_service.mark_file_checkpoint(db, run.id, filename, "error", str(exc))
                    await db.commit()
                except Exception:
                    await db.rollback()

    # Conflict detection once for the whole batch (more efficient than per-file)
    try:
        from app.services import conflict_service
        await conflict_service.detect_and_store(db)
    except Exception as e:
        logger.warning("Conflict detection failed for '%s' (non-fatal): %s", source_name, e)

    # Terminology scan over combined content
    try:
        from app.services import terminology_service
        combined = "\n\n".join(f["content"] for f in requests_map.values())
        await terminology_service.scan_content_and_update(db, combined, source_name)
    except Exception as e:
        logger.warning("Terminology scan failed for '%s' (non-fatal): %s", source_name, e)

    # Store aggregated file summaries on each Service record
    for module_name, summaries in module_file_summaries.items():
        if module_name in service_cache:
            service_cache[module_name].summary = "\n\n".join(summaries)
    if module_file_summaries:
        await db.commit()

    await _set_progress("Generating wiki pages…")
    # Wiki page generation — one page per module, best-effort
    try:
        from app.ingest.wiki_generator import generate_wiki_for_modules, RuleSummary
        from app.models.rule import Rule, RuleService
        from sqlalchemy import select as _select

        # Gather all rules for each module that was touched in this batch
        module_rules: dict[str, list[RuleSummary]] = {}
        for svc_name, svc_obj in service_cache.items():
            rows = (await db.execute(
                _select(Rule.id, Rule.title, Rule.definition)
                .join(RuleService, RuleService.rule_id == Rule.id)
                .where(RuleService.service_id == svc_obj.id)
            )).fetchall()
            rule_summaries = [RuleSummary(id=str(r[0]), title=r[1], definition=r[2]) for r in rows]
            if rule_summaries:
                module_rules[svc_name] = rule_summaries

        module_summaries = {m: "\n\n".join(s) for m, s in module_file_summaries.items()}
        await generate_wiki_for_modules(db, module_rules, module_summaries)
        await db.commit()
    except Exception as e:
        logger.warning("Wiki generation failed for '%s' (non-fatal): %s", source_name, e)

    # Derive the persisted run tallies from checkpoints (not the local pass counters):
    # on a resume the counters start at 0 and count only this pass, so they'd
    # under-report the cross-attempt totals. See DEC-045 / IV-001.
    done_count, errored_count = await ingest_service.count_checkpoint_tallies(db, run.id)
    await ingest_service.complete_run(
        db, run.id,
        status="completed" if errored_count == 0 else "completed_with_errors",
        files_processed=done_count,
        files_errored=errored_count,
        last_processed_file=last_file,
    )
    await db.commit()

    logger.info(
        "Batch ingest complete for '%s': %d rules from %d files (%d errored, %d this pass)",
        source_name, rules_extracted, done_count, errored_count, files_processed,
    )
    return {
        "rules_extracted": rules_extracted,
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "errors": errors,
    }
