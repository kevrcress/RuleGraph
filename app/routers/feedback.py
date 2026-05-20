"""
Feedback router — signal recording and graph improvement loop.

POST /feedback  — record any feedback signal (all users)
POST /improve   — apply feedback weights to graph nodes (Admin only)
POST /lint      — re-enrich graph structure via skills (Admin only)
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.rule import Rule
from sqlalchemy import select
from app.services import feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    signal_type: str
    rule_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None


@router.post("/feedback", status_code=201)
async def record_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Record a feedback signal for a rule."""
    if body.rule_id is None:
        raise HTTPException(status_code=400, detail="rule_id is required")

    # Verify rule exists
    result = await db.execute(select(Rule).where(Rule.id == body.rule_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Rule {body.rule_id} not found")

    user_id = uuid.UUID(current_user["sub"])
    fb = await feedback_service.record_signal(
        db=db,
        user_id=user_id,
        rule_id=body.rule_id,
        signal_type=body.signal_type,
    )
    await db.commit()
    return {
        "id": str(fb.id),
        "signal_type": fb.signal_type,
        "weight": fb.weight,
        "rule_id": str(fb.rule_id),
    }


@router.post("/improve")
async def run_improve(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """Aggregate all feedback signals and update graph_quality_score on Cognee nodes. Admin only."""
    result = await feedback_service.apply_improvements(db)
    await db.commit()
    return result


@router.post("/lint")
async def run_lint(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """Re-enrich the graph by re-ingesting all Cognee skills. Admin only."""
    try:
        from app.graph.cognee_client import ingest_skills
        await ingest_skills()
        return {"message": "Graph re-enrichment complete — skills re-ingested"}
    except Exception as exc:
        logger.warning("Lint failed (non-fatal): %s", exc)
        return {"message": "Graph re-enrichment attempted", "warning": str(exc)}
