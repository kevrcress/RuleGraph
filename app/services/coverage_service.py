"""
Coverage service — computes and returns rule coverage status.

Coverage is computed from the coverage_status column on rules.
Stage 2: all rules default to 'uncovered' unless a test file is explicitly
associated via the coverage_mapper.
"""
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule

logger = logging.getLogger(__name__)

VALID_STATUSES = {"covered", "partial", "uncovered", "coverage_gap", "stale"}


async def list_coverage_gaps(
    db: AsyncSession, page: int = 1, limit: int = 50
) -> tuple[list[Rule], int]:
    """
    Return rules with their coverage_status.
    Returns all rules so the UI can show the full coverage picture.
    """
    count_result = await db.execute(select(func.count()).select_from(Rule))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Rule)
        .order_by(Rule.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def update_rule_coverage(
    db: AsyncSession,
    rule_id,
    status: str,
) -> None:
    """Set coverage_status on a specific rule."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid coverage status: {status!r}")
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule:
        rule.coverage_status = status
        await db.flush()
