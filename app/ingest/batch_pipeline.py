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
_MAX_POLLS = 240          # 240 × 30s = 2 hours maximum wait


async def batch_ingest_files(
    db: AsyncSession,
    files: list[dict],
    source_name: str,
    src=None,
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

        run = await ingest_service.start_run(db, source_name)
        await db.commit()

        for custom_id, file_info in requests_map.items():
            filename = file_info["path"]
            last_file = filename
            await _set_progress(f"Processing {filename}…")

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

            files_processed += 1
            await db.commit()

    else:
        # Batch API path (Anthropic only)
        batch_requests = [
            build_batch_request(cid, fi["content"], fi["complexity"], threshold)
            for cid, fi in requests_map.items()
        ]

        _client = _get_client(await get_anthropic_api_key(db))
        await _set_progress(f"Scoring complete — submitting {len(batch_requests)} file(s) to AI…")
        logger.info("Submitting batch of %d files for source '%s'", len(batch_requests), source_name)

        batch = await _client.messages.batches.create(requests=batch_requests)
        await _set_progress(f"AI batch submitted ({len(batch_requests)} file(s)) — waiting for results…")
        logger.info("Batch %s submitted — polling every %ds for completion", batch.id, _POLL_INTERVAL)

        for poll_num in range(_MAX_POLLS):
            await asyncio.sleep(_POLL_INTERVAL)
            batch = await _client.messages.batches.retrieve(batch.id)
            elapsed_min = (poll_num + 1) * _POLL_INTERVAL // 60
            logger.debug("Batch %s status: %s (poll %d)", batch.id, batch.processing_status, poll_num + 1)
            if batch.processing_status == "ended":
                break
            if elapsed_min > 0:
                await _set_progress(f"AI processing… ({elapsed_min}m elapsed)")
        else:
            raise TimeoutError(
                f"Batch {batch.id} did not complete within {_MAX_POLLS * _POLL_INTERVAL}s"
            )

        await _set_progress("Processing AI results…")

        run = await ingest_service.start_run(db, source_name)
        await db.commit()

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
                continue

            if result.result.type != "succeeded":
                continue

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

            files_processed += 1
            await db.commit()

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

    await ingest_service.complete_run(
        db, run.id,
        status="completed" if not errors else "completed_with_errors",
        files_processed=files_processed,
        files_errored=files_errored,
        last_processed_file=last_file,
    )
    await db.commit()

    logger.info(
        "Batch ingest complete for '%s': %d rules from %d files (%d errors)",
        source_name, rules_extracted, files_processed, len(errors),
    )
    return {
        "rules_extracted": rules_extracted,
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "errors": errors,
    }
