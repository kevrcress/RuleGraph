"""
Wiki router — QA wiki promotion flow per Section 7.

POST /wiki/promote — promote approved QA changes to main wiki (TL + Admin only)
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.rule import Rule, RuleStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wiki", tags=["wiki"])


class WikiPromoteRequest(BaseModel):
    change_ids: list[str]


@router.post("/promote")
async def promote_wiki_changes(
    body: WikiPromoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    """
    Promote approved QA wiki changes to the main wiki.

    change_ids: list of rule UUIDs to promote, or ["all"] to promote all approved rules.
    Empty list is a no-op (returns 200 with no changes applied).
    """
    if not body.change_ids:
        return {"promoted": 0, "message": "No changes to promote"}

    if body.change_ids == ["all"]:
        # Promote all rules that are in 'approved' status
        result = await db.execute(
            select(Rule).where(Rule.status == RuleStatusEnum.approved)
        )
        rules_to_promote = result.scalars().all()
    else:
        # Validate UUIDs
        rule_uuids: list[uuid.UUID] = []
        for cid in body.change_ids:
            try:
                rule_uuids.append(uuid.UUID(cid))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid change_id: {cid!r}")

        result = await db.execute(
            select(Rule).where(Rule.id.in_(rule_uuids))
        )
        rules_to_promote = result.scalars().all()

        if not rules_to_promote:
            raise HTTPException(status_code=400, detail="No matching rules found for the provided change_ids")

    promoted = 0
    for rule in rules_to_promote:
        # Promote: move from approved → active (main wiki)
        if rule.status == RuleStatusEnum.approved:
            rule.status = RuleStatusEnum.active
            promoted += 1

    await db.flush()
    await db.commit()

    logger.info("Wiki promotion: %d rule(s) promoted to active by %s", promoted, current_user.get("sub"))
    return {"promoted": promoted, "message": f"{promoted} rule(s) promoted to main wiki"}
