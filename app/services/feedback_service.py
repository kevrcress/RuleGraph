"""
Feedback service — signal recording and graph quality score aggregation.

FEEDBACK_WEIGHTS is the single source of truth for all signal weights.
Never hardcode a weight inline elsewhere in the codebase.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.rule import Rule

logger = logging.getLogger(__name__)

FEEDBACK_WEIGHTS: dict[str, float] = {
    # Explicit signals
    "thumbs_up": 0.9,
    "thumbs_down": 0.2,
    "this_is_wrong": 0.1,
    "mark_as_verified": 1.0,
    # Implicit behavioral signals
    "clicked_through": 0.6,
    "clicked_source_doc": 0.7,
    "searched_again_immediately": 0.2,
    "edited_rule_after_view": 0.8,
    "conflict_resolved": 0.8,
    # Automated signals
    "drift_caught_and_resolved": 0.9,
    "coverage_gap_fixed": 0.8,
}


async def record_signal(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    rule_id: uuid.UUID,
    signal_type: str,
) -> Feedback:
    """Record a feedback signal and persist its weight from FEEDBACK_WEIGHTS."""
    weight = FEEDBACK_WEIGHTS.get(signal_type, 0.5)
    fb = Feedback(
        id=uuid.uuid4(),
        user_id=user_id,
        rule_id=rule_id,
        signal_type=signal_type,
        weight=weight,
    )
    db.add(fb)
    await db.flush()
    logger.info("Feedback recorded: signal=%s rule=%s weight=%.2f", signal_type, rule_id, weight)
    return fb


async def apply_improvements(db: AsyncSession) -> dict:
    """
    Aggregate all feedback signals per rule and update graph_quality_score.

    Score = weighted average of all signals recorded for that rule.
    This is called by POST /improve (Admin only).
    """
    all_feedback_result = await db.execute(select(Feedback))
    all_feedback = all_feedback_result.scalars().all()

    # Group signal weights by rule_id
    by_rule: dict[uuid.UUID, list[float]] = {}
    for fb in all_feedback:
        if fb.rule_id is not None:
            by_rule.setdefault(fb.rule_id, []).append(fb.weight)

    updated = 0
    for rule_id, weights in by_rule.items():
        rule_result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_result.scalar_one_or_none()
        if rule is not None:
            rule.graph_quality_score = sum(weights) / len(weights)
            updated += 1

    await db.flush()
    logger.info("apply_improvements: updated graph_quality_score on %d rules", updated)

    # Re-ingest skills to enrich graph (best-effort)
    try:
        from app.graph.cognee_client import ingest_skills
        await ingest_skills()
    except Exception as exc:
        logger.warning("Skill re-ingestion during improve failed (non-fatal): %s", exc)

    return {"rules_updated": updated, "message": "Graph quality scores updated from feedback signals"}
