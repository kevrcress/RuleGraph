"""
Source management router — CRUD for ingest sources + per-source ingest trigger.
All endpoints are Admin-only.

GET    /admin/sources
POST   /admin/sources
PUT    /admin/sources/{id}
DELETE /admin/sources/{id}
POST   /admin/sources/{id}/ingest
GET    /admin/ingest-runs/{id}
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.dependencies import require_roles
from app.ingest.batch_pipeline import batch_ingest_files
from app.models.ingest import IngestRun
from app.models.ingest_source import IngestSource
from app.schemas.ingest_source import (
    IngestSourceCreate,
    IngestSourceResponse,
    IngestSourceUpdate,
    IngestTriggerResponse,
    PaginatedSources,
)
from app.security.encryption import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/sources", tags=["sources"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _to_response(src: IngestSource) -> IngestSourceResponse:
    return IngestSourceResponse(
        id=src.id,
        name=src.name,
        source_type=src.source_type,
        repo_url=src.repo_url,
        branch=src.branch,
        paths=src.paths,
        exclude=src.exclude,
        test_paths=src.test_paths,
        has_pat=src.pat_encrypted is not None,
        created_at=src.created_at,
        last_ingested_at=src.last_ingested_at,
        status=src.status,
        ingest_status=src.ingest_status,
        ingest_error=src.ingest_error,
        ingest_progress=src.ingest_progress,
        last_commit_sha=src.last_commit_sha,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedSources)
async def list_sources(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    offset = (page - 1) * limit
    total = (await db.execute(select(func.count()).select_from(IngestSource))).scalar_one()
    rows = (await db.execute(
        select(IngestSource).order_by(IngestSource.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()
    return PaginatedSources(items=[_to_response(r) for r in rows], total=total)


@router.post("", response_model=IngestSourceResponse, status_code=201)
async def create_source(
    body: IngestSourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    existing = (await db.execute(select(IngestSource).where(IngestSource.name == body.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Source '{body.name}' already exists")

    src = IngestSource(
        id=uuid.uuid4(),
        name=body.name,
        source_type=body.source_type,
        repo_url=body.repo_url,
        branch=body.branch,
        paths=body.paths,
        exclude=body.exclude,
        test_paths=body.test_paths,
        pat_encrypted=encrypt_secret(body.pat) if body.pat else None,
        created_by=uuid.UUID(current_user["sub"]) if current_user.get("sub") else None,
        status="active",
    )
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return _to_response(src)


@router.put("/{source_id}", response_model=IngestSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    body: IngestSourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = (await db.execute(select(IngestSource).where(IngestSource.id == source_id))).scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")

    if body.name is not None:
        src.name = body.name
    if body.repo_url is not None:
        src.repo_url = body.repo_url
    if body.branch is not None:
        src.branch = body.branch
    if body.paths is not None:
        src.paths = body.paths
    if body.exclude is not None:
        src.exclude = body.exclude
    if body.test_paths is not None:
        src.test_paths = body.test_paths
    if body.pat is not None:
        src.pat_encrypted = encrypt_secret(body.pat)
    if body.status is not None:
        src.status = body.status

    await db.commit()
    await db.refresh(src)
    return _to_response(src)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = (await db.execute(select(IngestSource).where(IngestSource.id == source_id))).scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(src)
    await db.commit()


# ── Ingest trigger ────────────────────────────────────────────────────────────

async def _run_source_ingest(source_id: str) -> None:
    """Background task: clone repo, process every file through the pipeline."""
    from app.ingest.connectors.github_repo import GitHubRepoConnector

    async with async_session_factory() as db:
        src = (await db.execute(
            select(IngestSource).where(IngestSource.id == uuid.UUID(source_id))
        )).scalar_one_or_none()

        if not src:
            logger.error(f"Source {source_id} not found in background ingest task")
            return

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

            summary = await batch_ingest_files(db, files, src.name, src=src)
            errors = summary["errors"]

            src.last_ingested_at = datetime.now(timezone.utc)
            src.last_commit_sha = head_sha
            src.ingest_progress = None
            if errors:
                src.ingest_status = "error"
                src.ingest_error = f"{len(errors)} error(s). Last: {errors[-1]}"
            else:
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


@router.post("/{source_id}/ingest", response_model=IngestTriggerResponse)
async def trigger_ingest(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = (await db.execute(select(IngestSource).where(IngestSource.id == source_id))).scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    if src.status != "active":
        raise HTTPException(status_code=400, detail="Source is not active")
    if src.ingest_status == "ingesting":
        raise HTTPException(status_code=409, detail="Ingest already in progress for this source")

    background_tasks.add_task(_run_source_ingest, str(source_id))

    return IngestTriggerResponse(
        status="started",
        source_name=src.name,
        message=(
            f"Ingesting '{src.name}' from {src.repo_url} (branch: {src.branch}). "
            "This runs in the background — check /rules in a minute or two to see extracted rules."
        ),
    )


# ── Ingest run status (for polling) ──────────────────────────────────────────

@router.get("/{source_id}", response_model=IngestSourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = (await db.execute(select(IngestSource).where(IngestSource.id == source_id))).scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    return _to_response(src)
