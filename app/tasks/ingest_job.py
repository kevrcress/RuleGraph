"""Source ingest job implementation.

This module holds the actual ingest work (`run_ingest_impl`) extracted from the
sources router so it can run in either the FastAPI process (legacy fallback) or
the arq worker process. Import direction is one-way: routers and the arq worker
import from here; this module never imports them (avoids circular imports).
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.models.ingest import IngestRun
from app.models.ingest_source import IngestSource
from app.ingest.batch_pipeline import batch_ingest_files
from app.security.encryption import decrypt_secret

logger = logging.getLogger(__name__)


async def run_ingest_impl(source_id: str, resume: bool = False) -> None:
    """Clone repo, process every file through the pipeline.

    When ``resume`` is True, reuse the source's latest incomplete IngestRun and skip
    files already checkpointed ``done`` on that run. Opens its own DB session so it
    is safe to run from a background task or the arq worker process.
    """
    from app.ingest.connectors.github_repo import GitHubRepoConnector
    from app.services import ingest_service

    async with async_session_factory() as db:
        src = (await db.execute(
            select(IngestSource).where(IngestSource.id == uuid.UUID(source_id))
        )).scalar_one_or_none()

        if not src:
            logger.error(f"Source {source_id} not found in background ingest task")
            return

        resume_run: IngestRun | None = None
        done_paths: set[str] = set()
        if resume:
            resume_run = await ingest_service.find_resumable_run(db, src)
            if resume_run is None:
                logger.warning(f"Resume requested for source '{src.name}' but no incomplete run found")
                return
            # Already-done files don't need re-reading; pass them to the connector so it
            # skips loading their content into memory on resume (DEC-045 follow-up).
            done_paths = await ingest_service.get_done_files(db, resume_run.id)

        pat = decrypt_secret(src.pat_encrypted) if src.pat_encrypted else None

        if src.source_type == "github_repo":
            connector = GitHubRepoConnector(
                repo_url=src.repo_url,
                pat=pat,
                branch=src.branch,
                paths=src.paths,
                exclude=src.exclude,
                test_paths=src.test_paths,
                last_commit_sha=src.last_commit_sha,
                skip_paths=done_paths,
            )
        else:
            msg = f"Unsupported source_type '{src.source_type}'"
            logger.error(f"Source {src.name}: {msg}")
            src.ingest_status = "error"
            src.ingest_error = msg
            await db.commit()
            return

        src.ingest_status = "ingesting"
        src.ingest_error = None
        src.ingest_progress = "Cloning repository…"
        await db.commit()

        try:
            try:
                files, head_sha = await connector.list_files()
            except Exception as e:
                logger.error(f"Failed to clone/list files for source '{src.name}': {e}")
                src.ingest_status = "error"
                src.ingest_error = f"Failed to fetch repository: {e}"
                src.ingest_progress = None
                await db.commit()
                return

            if not files:
                logger.info(f"No changed files for source '{src.name}' since {src.last_commit_sha[:8] if src.last_commit_sha else 'N/A'} — skipping batch")
                src.last_ingested_at = datetime.now(timezone.utc)
                src.last_commit_sha = head_sha
                src.ingest_status = "idle"
                src.ingest_error = None
                src.ingest_progress = None
                await db.commit()
                return

            mode = "incremental" if src.last_commit_sha else "full"
            logger.info(f"Processing {len(files)} files for source '{src.name}' ({mode}) via Batches API…")

            summary = await batch_ingest_files(
                db, files, src.name, src=src, resume_run=resume_run, resume=resume
            )
            errors = summary["errors"]

            src.last_ingested_at = datetime.now(timezone.utc)
            src.ingest_progress = None
            if errors:
                src.ingest_status = "error"
                src.ingest_error = f"{len(errors)} error(s). Last: {errors[-1]}"
                # Do NOT advance last_commit_sha on an errored run: the failed files must
                # remain inside the incremental diff window so a later plain re-trigger still
                # re-lists them (Resume recovers them via error checkpoints regardless).
            else:
                src.last_commit_sha = head_sha
                src.ingest_status = "idle"
                src.ingest_error = None
            await db.commit()
            logger.info(
                f"Batch ingest complete for source '{src.name}' ({mode}): "
                f"{summary['rules_extracted']} rules from {summary['files_processed']} files"
            )

        except Exception as e:
            logger.exception(f"Unexpected error during ingest of '{src.name}': {e}")
            try:
                # Rollback first — the session may be in a DB error state from a
                # failed flush, and committing on a dirty session also fails.
                await db.rollback()
                src.ingest_status = "error"
                src.ingest_error = f"Unexpected error: {e}"
                src.ingest_progress = None
                await db.commit()
            except Exception:
                pass
