"""Unit tests for the reconciled Batch poll budget (DEC-045).

The poll budget must stay strictly below the arq job_timeout (so the poll loop
self-times-out before arq SIGKILLs the worker) and the stale threshold must stay
above the job_timeout (so the sweep can't pre-empt arq). Invariant:

    poll_budget < job_timeout < stale_threshold
"""
from app.config import settings
from app.ingest.batch_pipeline import _POLL_INTERVAL, _max_polls


def test_poll_budget_is_strictly_below_job_timeout():
    poll_budget = _max_polls() * _POLL_INTERVAL
    assert poll_budget < settings.ingest_job_timeout_seconds, (
        f"poll_budget {poll_budget}s must be < job_timeout "
        f"{settings.ingest_job_timeout_seconds}s so the loop times out before arq kill"
    )


def test_timing_invariant_holds_with_defaults():
    poll_budget = _max_polls() * _POLL_INTERVAL
    job_timeout = settings.ingest_job_timeout_seconds
    stale_threshold = job_timeout + settings.ingest_stale_grace_seconds
    assert poll_budget < job_timeout < stale_threshold


def test_max_polls_floors_at_one_when_reserve_exceeds_timeout(monkeypatch):
    # A misconfiguration where the reserve >= job_timeout must still yield at least
    # one poll rather than range(0) (which would never wait for the batch at all).
    monkeypatch.setattr(settings, "ingest_batch_poll_reserve_seconds", 999_999)
    assert _max_polls() == 1
