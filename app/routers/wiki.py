"""
Wiki router — auto-generated documentation browser and admin operations.

GET  /wiki              — paginated list of generated wiki pages
GET  /wiki/{id}         — single page with linked rules
POST /wiki/regenerate   — re-generate all wiki pages from current rules (Admin)
POST /wiki/promote      — promote approved QA rules to active (TL + Admin)
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.dependencies import get_current_user, require_roles
from app.models.wiki import WikiPage
from app.models.rule import Rule, RuleService, Service, RuleStatusEnum
from app.schemas.wiki import WikiPageItem, WikiPageDetail, PaginatedWikiPages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wiki", tags=["wiki"])

_SORT_COLUMNS = {
    "title":            WikiPage.title,
    "updated_at":       WikiPage.updated_at,
    "last_generated_at": WikiPage.last_generated_at,
    "module":           WikiPage.module,
}


@router.get("", response_model=PaginatedWikiPages)
async def list_wiki_pages(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="updated_at"),
    order: str = Query(default="desc"),
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    sort_col = _SORT_COLUMNS.get(sort, WikiPage.updated_at)
    order_fn = asc if order == "asc" else desc
    offset = (page - 1) * limit

    base_q = select(WikiPage)
    if search:
        like = f"%{search}%"
        base_q = base_q.where(WikiPage.title.ilike(like) | WikiPage.content.ilike(like) | WikiPage.module.ilike(like))

    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()
    rows = (await db.execute(base_q.order_by(order_fn(sort_col)).offset(offset).limit(limit))).scalars().all()

    return PaginatedWikiPages(
        items=[WikiPageItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{page_id}", response_model=WikiPageDetail)
async def get_wiki_page(
    page_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = (await db.execute(select(WikiPage).where(WikiPage.id == page_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Wiki page {page_id} not found")

    # Resolve linked rules to {id, title, status} for the frontend
    linked_rules: list[dict] = []
    if row.linked_rule_ids:
        rule_uuids = [uuid.UUID(rid) for rid in row.linked_rule_ids if rid]
        if rule_uuids:
            rules = (await db.execute(
                select(Rule.id, Rule.title, Rule.status).where(Rule.id.in_(rule_uuids))
            )).fetchall()
            linked_rules = [{"id": str(r[0]), "title": r[1], "status": r[2].value} for r in rules]

    return WikiPageDetail(
        **WikiPageItem.model_validate(row).model_dump(),
        linked_rules=linked_rules,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Admin: regenerate all wiki pages
# ──────────────────────────────────────────────────────────────────────────────

async def _run_regenerate() -> dict:
    """Re-generate wiki pages for every service module in the DB."""
    from app.ingest.wiki_generator import generate_wiki_for_modules, RuleSummary

    async with async_session_factory() as db:
        try:
            # Group all rules by their service module
            rows = (await db.execute(
                select(Service.name, Rule.id, Rule.title, Rule.definition)
                .join(RuleService, RuleService.service_id == Service.id)
                .join(Rule, Rule.id == RuleService.rule_id)
            )).fetchall()

            module_rules: dict[str, list[RuleSummary]] = {}
            for svc_name, rule_id, title, definition in rows:
                module_rules.setdefault(svc_name, []).append(
                    RuleSummary(id=str(rule_id), title=title, definition=definition)
                )

            # Pull stored code summaries from Service records so wiki has full context
            svc_rows = (await db.execute(select(Service.name, Service.summary))).fetchall()
            module_summaries = {name: summary for name, summary in svc_rows if summary}

            written = await generate_wiki_for_modules(db, module_rules, module_summaries)
            await db.commit()
            return {"pages_generated": len(written), "modules": list(written.keys())}
        except Exception:
            await db.rollback()
            raise


@router.post("/regenerate")
async def regenerate_wiki(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """Re-generate all wiki pages from current rules. Runs in the background."""
    background_tasks.add_task(_run_regenerate)
    return {"status": "started", "message": "Wiki regeneration running in background."}


# ──────────────────────────────────────────────────────────────────────────────
# QA promotion (existing)
# ──────────────────────────────────────────────────────────────────────────────

class WikiPromoteRequest(BaseModel):
    change_ids: list[str]


@router.post("/promote")
async def promote_wiki_changes(
    body: WikiPromoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    if not body.change_ids:
        return {"promoted": 0, "message": "No changes to promote"}

    if body.change_ids == ["all"]:
        rules_to_promote = (await db.execute(
            select(Rule).where(Rule.status == RuleStatusEnum.approved)
        )).scalars().all()
    else:
        rule_uuids: list[uuid.UUID] = []
        for cid in body.change_ids:
            try:
                rule_uuids.append(uuid.UUID(cid))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid change_id: {cid!r}")

        rules_to_promote = (await db.execute(
            select(Rule).where(Rule.id.in_(rule_uuids))
        )).scalars().all()

        if not rules_to_promote:
            raise HTTPException(status_code=400, detail="No matching rules found")

    promoted = 0
    for rule in rules_to_promote:
        if rule.status == RuleStatusEnum.approved:
            rule.status = RuleStatusEnum.active
            promoted += 1

    await db.flush()
    await db.commit()
    logger.info("Wiki promotion: %d rule(s) promoted by %s", promoted, current_user.get("sub"))
    return {"promoted": promoted, "message": f"{promoted} rule(s) promoted to main wiki"}
