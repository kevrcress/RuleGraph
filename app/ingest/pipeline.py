"""
Ingest pipeline — orchestrates per-file processing.
Steps:
  1. Score complexity
  2. Route to correct LLM tier
  3. Extract business rules
  4. Add to Cognee (best-effort)
  5. Associate with service
  6. Store extracted rules in Postgres
  7. Run conflict detection (best-effort)
  8. Run terminology scan (best-effort)
"""
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.complexity import score_complexity
from app.ingest.extractor import extract_rules
from app.graph.cognee_client import add_to_graph
from app.services import ingest_service

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    rules_extracted: int = 0
    errors: list[str] = field(default_factory=list)
    run_id: Optional[uuid.UUID] = None


async def process_file(
    db: AsyncSession,
    filename: str,
    content: str,
    source_name: Optional[str] = None,
) -> IngestResult:
    """
    Process a single file through the full ingest pipeline.

    Args:
        db: Async database session.
        filename: Name of the file being processed.
        content: Text content of the file.
        source_name: Optional label for the ingest source / service name.

    Returns:
        IngestResult with rules_extracted count and any errors.
    """
    result = IngestResult()
    effective_source = source_name or "file_upload"

    # Start ingest run tracking
    run = await ingest_service.start_run(db, effective_source)
    result.run_id = run.id
    await db.commit()

    files_errored = 0

    try:
        # --- Step 1: Score complexity ---
        complexity = score_complexity(content)
        logger.info(f"File '{filename}' complexity score: {complexity:.3f}")

        # --- Step 2 & 3: Extract business rules via LLM with retry ---
        extraction_result_holder, extraction_error = await ingest_service.with_retry(
            "llm_extraction",
            lambda: extract_rules(content, complexity),
        )

        if extraction_error or extraction_result_holder is None:
            error_msg = str(extraction_error) if extraction_error else "Extraction returned None"
            logger.error(f"LLM extraction failed for '{filename}': {error_msg}")
            await ingest_service.log_error(
                db=db,
                run_id=run.id,
                source_name=effective_source,
                file_path=filename,
                error_source="llm_extraction",
                error_message=error_msg,
                raw_content=content[:5000],
                stack_trace=traceback.format_exc() if extraction_error else None,
            )
            files_errored += 1
            await ingest_service.complete_run(
                db, run.id, "failed",
                files_processed=0, files_errored=files_errored,
                last_processed_file=filename,
            )
            await db.commit()
            result.errors.append(error_msg)
            return result

        extraction_result = extraction_result_holder

        if extraction_result.error:
            logger.error(f"LLM extraction error for '{filename}': {extraction_result.error}")
            await ingest_service.log_error(
                db=db,
                run_id=run.id,
                source_name=effective_source,
                file_path=filename,
                error_source="llm_extraction",
                error_message=extraction_result.error,
                raw_content=content[:5000],
            )
            files_errored += 1
            await ingest_service.complete_run(
                db, run.id, "failed",
                files_processed=0, files_errored=files_errored,
                last_processed_file=filename,
            )
            await db.commit()
            result.errors.append(extraction_result.error)
            return result

        extracted_rules = extraction_result.rules
        logger.info(
            f"Extracted {len(extracted_rules)} rules from '{filename}' "
            f"using {extraction_result.model_used}"
        )

        # --- Step 4: Add to Cognee (best-effort) ---
        cognee_node_id = await add_to_graph(content, dataset_name="rulegraph")
        if cognee_node_id is None:
            logger.info(f"Cognee graph enrichment skipped/failed for '{filename}' (non-fatal)")

        # --- Step 5: Get or create the service record ---
        service = await ingest_service.get_or_create_service(db, effective_source)
        await db.flush()

        # --- Step 6: Store each rule in Postgres with service association ---
        for extracted in extracted_rules:
            try:
                await ingest_service.store_rule(
                    db=db,
                    title=extracted.title,
                    definition=extracted.definition,
                    confidence=extracted.confidence,
                    source_type="code" if effective_source != "file_upload" else "file_upload",
                    cognee_node_id=cognee_node_id,
                    service_id=service.id,
                )
                result.rules_extracted += 1
            except Exception as store_exc:
                logger.error(f"Failed to store rule '{extracted.title}': {store_exc}")
                result.errors.append(f"Failed to store rule '{extracted.title}': {store_exc}")

        # --- Step 7: Run conflict detection (best-effort, non-fatal) ---
        try:
            from app.services import conflict_service
            await conflict_service.detect_and_store(db)
        except Exception as e:
            logger.warning(f"Conflict detection failed for '{filename}' (non-fatal): {e}")

        # --- Step 8: Run terminology scan (best-effort, non-fatal) ---
        try:
            from app.services import terminology_service
            await terminology_service.scan_content_and_update(db, content, effective_source)
        except Exception as e:
            logger.warning(f"Terminology scan failed for '{filename}' (non-fatal): {e}")

        # --- Complete the run ---
        await ingest_service.complete_run(
            db, run.id,
            status="completed" if not result.errors else "completed_with_errors",
            files_processed=1,
            files_errored=files_errored,
            last_processed_file=filename,
        )
        await db.commit()

    except Exception as e:
        logger.exception(f"Unexpected pipeline error for '{filename}': {e}")
        result.errors.append(str(e))
        try:
            await ingest_service.complete_run(
                db, run.id, "failed",
                files_processed=0, files_errored=1,
                last_processed_file=filename,
            )
            await db.commit()
        except Exception:
            pass

    return result
