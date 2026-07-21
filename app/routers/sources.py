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
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.ingest import IngestRun, IngestFileCheckpoint
from app.models.ingest_source import IngestSource
from app.routers._deps import require_arq_pool
from app.services import ingest_service
from app.services.settings_service import get_ingest_stale_threshold
from app.tasks.recovery import staleness_exceeded
from app.tasks.queue import INGEST_QUEUE_NAME
from app.schemas.ingest import (
    IngestFileCheckpointResponse,
    IngestRunResponse,
    PaginatedCheckpoints,
)
from app.schemas.ingest_source import (
    IngestSourceCreate,
    IngestSourceResponse,
    IngestSourceUpdate,
    IngestTriggerResponse,
    PaginatedSources,
)
from app.security.encryption import encrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/sources", tags=["sources"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _to_response(
    src: IngestSource,
    progress: "dict | None" = None,
) -> IngestSourceResponse:
    progress = progress or {}
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
        run_status=progress.get("run_status"),
        done_file_count=progress.get("done", 0),
        total_file_count=progress.get("total", 0),
        run_is_stale=progress.get("run_is_stale", False),
        can_resume=progress.get("can_resume", False),
    )


async def _runs_progress_for_sources(db: AsyncSession, srcs: list[IngestSource]) -> dict[str, dict]:
    """Batched latest-run progress for many sources — avoids the per-row N+1.

    Returns ``{source_name: {run_status, done, total, run_is_stale, can_resume}}``. A handful
    of set-based queries replace ~4 queries per source. ``run_is_stale`` and ``can_resume`` use
    the SAME shared predicates as the recovery cron sweep (``staleness_exceeded``) and the
    server-side resume gate (``is_run_resumable``) so the UI and the server can never disagree.
    """
    if not srcs:
        return {}

    names = [s.name for s in srcs]
    # Latest run per source in one query (DISTINCT ON), matching latest_run_for_source's ordering.
    latest_runs = (await db.execute(
        select(IngestRun)
        .where(IngestRun.source_name.in_(names))
        .order_by(IngestRun.source_name, IngestRun.started_at.desc(), IngestRun.id.desc())
        .distinct(IngestRun.source_name)
    )).scalars().all()
    run_by_name = {r.source_name: r for r in latest_runs}
    run_ids = [r.id for r in latest_runs]

    done_by_run: dict = {}
    total_by_run: dict = {}
    last_progress_by_run: dict = {}
    if run_ids:
        for run_id, status, cnt in (await db.execute(
            select(IngestFileCheckpoint.ingest_run_id, IngestFileCheckpoint.status, func.count())
            .where(IngestFileCheckpoint.ingest_run_id.in_(run_ids))
            .group_by(IngestFileCheckpoint.ingest_run_id, IngestFileCheckpoint.status)
        )).all():
            total_by_run[run_id] = total_by_run.get(run_id, 0) + cnt
            if status == "done":
                done_by_run[run_id] = done_by_run.get(run_id, 0) + cnt
        last_progress_by_run = {
            run_id: ts for run_id, ts in (await db.execute(
                select(IngestFileCheckpoint.ingest_run_id, func.max(IngestFileCheckpoint.processed_at))
                .where(IngestFileCheckpoint.ingest_run_id.in_(run_ids))
                .where(IngestFileCheckpoint.processed_at.is_not(None))
                .group_by(IngestFileCheckpoint.ingest_run_id)
            )).all()
        }

    threshold = await get_ingest_stale_threshold(db)
    now = datetime.now(timezone.utc)
    out: dict[str, dict] = {}
    for src in srcs:
        run = run_by_name.get(src.name)
        if run is None:
            out[src.name] = {"run_status": None, "done": 0, "total": 0, "run_is_stale": False, "can_resume": False}
            continue
        done = done_by_run.get(run.id, 0)
        total = total_by_run.get(run.id, 0)
        # Mirror recovery.is_run_stale: newest of checkpoint progress, the Batch poll
        # heartbeat, else started_at — so the list view's staleness agrees with the
        # cron sweep even while a batch is mid-poll (DEC-045).
        progress_candidates = [
            ts for ts in (last_progress_by_run.get(run.id), run.last_heartbeat_at) if ts is not None
        ]
        last_progress = max(progress_candidates) if progress_candidates else run.started_at
        out[src.name] = {
            "run_status": run.status,
            "done": done,
            "total": total,
            "run_is_stale": staleness_exceeded(last_progress, threshold, now),
            "can_resume": ingest_service.is_run_resumable(run.status, src.ingest_status) and done < total,
        }
    return out


async def _get_source_by_id(db: AsyncSession, source_id: uuid.UUID) -> IngestSource:
    src = (await db.execute(select(IngestSource).where(IngestSource.id == source_id))).scalar_one_or_none()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return src


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
    progress = await _runs_progress_for_sources(db, list(rows))
    items = [_to_response(r, progress.get(r.name)) for r in rows]
    return PaginatedSources(items=items, total=total)


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
    src = await _get_source_by_id(db, source_id)

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
    src = await _get_source_by_id(db, source_id)
    await db.delete(src)
    await db.commit()


# ── Ingest trigger ────────────────────────────────────────────────────────────

# The ingest job body lives in app/tasks/ingest_job.run_ingest_impl and runs in the
# arq worker process (see app/tasks/worker.py); routers only enqueue jobs. The shared
# resume/staleness predicates live in app/services/ingest_service.


@router.post("/{source_id}/ingest", response_model=IngestTriggerResponse)
async def trigger_ingest(
    source_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = await _get_source_by_id(db, source_id)
    if src.status != "active":
        raise HTTPException(status_code=400, detail="Source is not active")
    if src.ingest_status == "ingesting":
        raise HTTPException(status_code=409, detail="Ingest already in progress for this source")

    pool = require_arq_pool(request)
    await pool.enqueue_job(
        "run_source_ingest", str(source_id), False, _queue_name=INGEST_QUEUE_NAME
    )

    return IngestTriggerResponse(
        status="started",
        source_name=src.name,
        message=(
            f"Ingesting '{src.name}' from {src.repo_url} (branch: {src.branch}). "
            "This runs in the background — check /rules in a minute or two to see extracted rules."
        ),
    )


@router.post("/{source_id}/resume", response_model=IngestTriggerResponse)
async def resume_ingest(
    source_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """Resume the source's latest incomplete ingest run, skipping already-done files."""
    src = await _get_source_by_id(db, source_id)
    if src.ingest_status == "ingesting":
        raise HTTPException(status_code=409, detail="Ingest already in progress for this source")

    pool = require_arq_pool(request)

    resume_run = await ingest_service.find_resumable_run(db, src)
    if resume_run is None:
        raise HTTPException(status_code=409, detail="No resumable ingest run for this source")

    await pool.enqueue_job(
        "run_source_ingest", str(source_id), True, _queue_name=INGEST_QUEUE_NAME
    )

    return IngestTriggerResponse(
        status="resumed",
        source_name=src.name,
        run_id=str(resume_run.id),
        message=(
            f"Resuming ingest of '{src.name}' — skipping files already processed. "
            "This runs in the background — check /rules in a minute or two."
        ),
    )


@router.post("/{source_id}/retry-errors", response_model=IngestTriggerResponse)
async def retry_errors_ingest(
    source_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """Reset all errored file checkpoints to pending and re-queue the ingest worker."""
    src = await _get_source_by_id(db, source_id)
    if src.ingest_status == "ingesting":
        raise HTTPException(status_code=409, detail="Ingest already in progress for this source")

    run = await ingest_service.latest_run_for_source(db, src.name)
    if run is None:
        raise HTTPException(status_code=409, detail="No ingest run found for this source")

    pool = require_arq_pool(request)

    reset_count = await ingest_service.reset_error_checkpoints_for_retry(db, run)
    if reset_count == 0:
        raise HTTPException(status_code=400, detail="No errored files to retry for this source")

    await db.commit()

    await pool.enqueue_job(
        "run_source_ingest", str(source_id), True, _queue_name=INGEST_QUEUE_NAME
    )

    return IngestTriggerResponse(
        status="queued",
        source_name=src.name,
        run_id=str(run.id),
        message=(
            f"Retrying {reset_count} errored file(s) for '{src.name}'. "
            "This runs in the background — refresh in a moment to see progress."
        ),
    )


@router.get("/{source_id}/ingest-runs/latest/files", response_model=PaginatedCheckpoints)
async def get_latest_ingest_files(
    source_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = await _get_source_by_id(db, source_id)

    run_result = await db.execute(
        select(IngestRun)
        .where(IngestRun.source_name == src.name)
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .limit(1)
    )
    run = run_result.scalar_one_or_none()

    if run is None:
        return PaginatedCheckpoints(items=[], total=0, run=None)

    count_result = await db.execute(
        select(func.count()).where(IngestFileCheckpoint.ingest_run_id == run.id)
    )
    total = count_result.scalar_one()

    errored_count_result = await db.execute(
        select(func.count()).where(
            IngestFileCheckpoint.ingest_run_id == run.id,
            IngestFileCheckpoint.status == "error",
        )
    )
    live_errored = errored_count_result.scalar_one()

    offset = (page - 1) * page_size
    items_result = await db.execute(
        select(IngestFileCheckpoint)
        .where(IngestFileCheckpoint.ingest_run_id == run.id)
        .order_by(IngestFileCheckpoint.file_path.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = items_result.scalars().all()

    run_response = IngestRunResponse.model_validate(run)
    run_response.files_errored = live_errored

    return PaginatedCheckpoints(
        items=[IngestFileCheckpointResponse.model_validate(c) for c in items],
        total=total,
        run=run_response,
    )


# ── Ingest run status (for polling) ──────────────────────────────────────────

@router.get("/{source_id}", response_model=IngestSourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    src = await _get_source_by_id(db, source_id)
    progress = await _runs_progress_for_sources(db, [src])
    return _to_response(src, progress.get(src.name))
