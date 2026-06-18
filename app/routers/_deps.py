"""Shared FastAPI dependencies/guards for the router layer."""
from arq.connections import ArqRedis
from fastapi import HTTPException, Request


def require_arq_pool(request: Request) -> ArqRedis:
    """Return the arq pool, or raise 503 if it was never created (Redis down at boot).

    When Redis is unreachable at startup, ``app/main.py`` leaves ``app.state.arq_pool``
    as None. Dereferencing it for ``.enqueue_job`` would raise AttributeError and
    surface as an opaque 500. This guard turns that into a clear 503 instead.

    Single source of truth for the guard and its 503 detail string, shared by the
    sources router (trigger/resume) and the ingest router (ingest-all).
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Ingest queue unavailable — background worker/Redis not reachable",
        )
    return pool
