"""
Impact analysis service — upstream/downstream dependency traversal per Section 21.

GET /rules/{id}/impact   — what does this rule affect?
GET /rules/{id}/impact/reverse — what affects this rule?
"""
import uuid
import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleService, Service
from app.models.document import Document, RuleDocument
from app.models.notification import Subscription

logger = logging.getLogger(__name__)


async def get_impact(
    db: AsyncSession,
    rule_id: uuid.UUID,
    view: str = "technical",
) -> dict:
    """
    Compute what this rule affects.

    Returns services, related rules, tests, documents, and subscribed_count.
    In business view, file paths and technical details are stripped.
    """
    # 1. Services that implement this rule
    services_result = await db.execute(
        select(Service)
        .join(RuleService, RuleService.service_id == Service.id)
        .where(RuleService.rule_id == rule_id)
    )
    service_rows = services_result.scalars().all()

    services = [{"id": str(s.id), "name": s.name} for s in service_rows]

    # 2. Related rules — rules linked to the same services
    related_rules: list[dict] = []
    if service_rows:
        service_ids = [s.id for s in service_rows]
        other_rules_result = await db.execute(
            select(Rule)
            .join(RuleService, RuleService.rule_id == Rule.id)
            .where(
                RuleService.service_id.in_(service_ids),
                Rule.id != rule_id,
            )
            .distinct()
            .limit(10)
        )
        other_rules = other_rules_result.scalars().all()
        related_rules = [
            {"id": str(r.id), "title": r.title, "status": r.status.value}
            for r in other_rules
        ]

    # 3. Tests — represented by coverage_status and associated test info
    rule_result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_result.scalar_one_or_none()
    tests: list[dict] = []
    if rule and rule.coverage_status and rule.coverage_status != "uncovered":
        tests = [{"name": f"coverage:{rule.coverage_status}", "status": rule.coverage_status}]

    # 4. Documents that reference this rule
    docs_result = await db.execute(
        select(Document)
        .join(RuleDocument, RuleDocument.document_id == Document.id)
        .where(RuleDocument.rule_id == rule_id)
    )
    doc_rows = docs_result.scalars().all()
    documents = [{"id": str(d.id), "filename": d.filename} for d in doc_rows]

    # 5. Subscribed user count
    sub_count_result = await db.execute(
        select(func.count())
        .select_from(Subscription)
        .where(
            Subscription.target_type == "rule",
            Subscription.target_id == rule_id,
        )
    )
    subscribed_count = sub_count_result.scalar_one()

    # Build response — business view strips technical details
    if view == "business":
        return {
            "rule_id": str(rule_id),
            "summary": _build_business_summary(services, related_rules, tests, subscribed_count),
            "services": [{"name": s["name"]} for s in services],
            "rules": [{"title": r["title"], "status": r["status"]} for r in related_rules],
            "tests": [{"status": t["status"]} for t in tests],
            "documents": [{"filename": d["filename"]} for d in documents],
            "subscribed_count": subscribed_count,
        }
    else:
        return {
            "rule_id": str(rule_id),
            "services": services,
            "rules": related_rules,
            "tests": tests,
            "documents": documents,
            "subscribed_count": subscribed_count,
        }


async def get_reverse_impact(
    db: AsyncSession,
    rule_id: uuid.UUID,
    view: str = "technical",
) -> dict:
    """
    What affects this rule? (reverse dependency traversal)

    Finds rules that reference the same concepts and services that depend on this rule.
    """
    # Get this rule's services
    services_result = await db.execute(
        select(Service)
        .join(RuleService, RuleService.service_id == Service.id)
        .where(RuleService.rule_id == rule_id)
    )
    service_rows = services_result.scalars().all()
    services = [{"id": str(s.id), "name": s.name} for s in service_rows]

    # Rules that share terminology with this rule (heuristic for upstream deps)
    rule_result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_result.scalar_one_or_none()

    upstream_rules: list[dict] = []
    if rule:
        words = set(rule.title.lower().split())
        # Find rules whose titles share significant terms
        all_rules_result = await db.execute(
            select(Rule).where(Rule.id != rule_id).limit(100)
        )
        all_rules = all_rules_result.scalars().all()
        for r in all_rules:
            r_words = set(r.title.lower().split())
            if len(words & r_words) >= 1 and words & r_words - {"the", "a", "an", "of", "in"}:
                upstream_rules.append({"id": str(r.id), "title": r.title, "status": r.status.value})
        upstream_rules = upstream_rules[:5]

    if view == "business":
        return {
            "rule_id": str(rule_id),
            "upstream_services": [{"name": s["name"]} for s in services],
            "upstream_rules": [{"title": r["title"], "status": r["status"]} for r in upstream_rules],
        }
    else:
        return {
            "rule_id": str(rule_id),
            "upstream_services": services,
            "upstream_rules": upstream_rules,
        }


def _build_business_summary(
    services: list[dict],
    related_rules: list[dict],
    tests: list[dict],
    subscribed_count: int,
) -> str:
    parts = []
    if services:
        names = ", ".join(s["name"] for s in services)
        parts.append(f"Affects {len(services)} service(s): {names}")
    if related_rules:
        parts.append(f"{len(related_rules)} related rule(s)")
    if tests:
        parts.append(f"{len(tests)} test(s) cover this rule")
    if subscribed_count:
        parts.append(f"{subscribed_count} subscriber(s) will be notified")
    return ". ".join(parts) if parts else "No downstream dependencies found."
