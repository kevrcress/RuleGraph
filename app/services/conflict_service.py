"""
Conflict service — detects and stores cross-service rule conflicts.

Detection approach: keyword-based overlap.
Two rules from different services are flagged as conflicting when they share
2+ significant business terms from the same semantic cluster.
"""
import logging
import re
import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conflict import Conflict
from app.models.rule import Rule, RuleService, Service

logger = logging.getLogger(__name__)

# Significant business terms — words that indicate business rules (not stopwords)
SIGNIFICANT_TERMS: frozenset = frozenset({
    "stock", "inventory", "availability", "available",
    "payment", "billing", "charge", "authorize", "authorization",
    "cancel", "cancellation",
    "order", "ordering",
    "fee", "penalty", "late",
    "grace", "period", "window",
    "confirm", "confirmation", "validate", "validation",
    "buyer", "customer", "client", "identity",
    "submit", "approval", "approve", "reject",
    "threshold", "limit", "maximum", "minimum",
    "credit", "debit", "balance",
    "ship", "shipping", "delivery",
    "refund", "return",
})

CONFLICT_MIN_SHARED = 2


def _extract_keywords(text: str) -> frozenset:
    """Extract significant business keywords from rule text."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return frozenset(w for w in words if w in SIGNIFICANT_TERMS)


async def detect_and_store(db: AsyncSession) -> list[Conflict]:
    """
    Re-run full conflict detection across all rules. Replaces existing conflicts.
    Called after every file ingest to keep conflicts current.
    """
    try:
        # Load all rules with their service associations
        result = await db.execute(
            select(Rule, Service.name)
            .join(RuleService, RuleService.rule_id == Rule.id, isouter=True)
            .join(Service, Service.id == RuleService.service_id, isouter=True)
        )
        rows = result.all()

        # Group rules by service (deduplicate rules that appear in multiple joins)
        rules_by_service: dict[str, list[Rule]] = {}
        seen_rule_ids: set = set()
        for rule, service_name in rows:
            if rule.id in seen_rule_ids:
                continue
            seen_rule_ids.add(rule.id)
            svc = service_name or "unknown"
            rules_by_service.setdefault(svc, []).append(rule)

        service_names = list(rules_by_service.keys())
        if len(service_names) < 2:
            logger.info("Conflict detection: fewer than 2 services, no conflicts possible")
            await db.execute(delete(Conflict))
            await db.flush()
            return []

        # Find conflicts between different services
        new_conflicts: list[dict] = []
        seen_pairs: set = set()

        for i, svc_a in enumerate(service_names):
            for svc_b in service_names[i + 1:]:
                if svc_a == svc_b:
                    continue
                for rule_a in rules_by_service[svc_a]:
                    for rule_b in rules_by_service[svc_b]:
                        pair_key = tuple(sorted([str(rule_a.id), str(rule_b.id)]))
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)

                        kw_a = _extract_keywords(f"{rule_a.title} {rule_a.definition}")
                        kw_b = _extract_keywords(f"{rule_b.title} {rule_b.definition}")
                        shared = kw_a & kw_b

                        if len(shared) >= CONFLICT_MIN_SHARED:
                            new_conflicts.append({
                                "description": (
                                    f"Potential conflict between {svc_a!r} and {svc_b!r}: "
                                    f"both services define rules sharing concepts: "
                                    f"{', '.join(sorted(shared))}. "
                                    f"Rules: '{rule_a.title}' ({svc_a}) vs "
                                    f"'{rule_b.title}' ({svc_b})."
                                ),
                                "services": sorted([svc_a, svc_b]),
                                "rule_ids": [str(rule_a.id), str(rule_b.id)],
                                "severity": "medium",
                            })

        # Replace all existing conflicts
        await db.execute(delete(Conflict))

        stored: list[Conflict] = []
        for c in new_conflicts:
            conflict = Conflict(
                id=uuid.uuid4(),
                description=c["description"],
                services=c["services"],
                rule_ids=c["rule_ids"],
                severity=c["severity"],
            )
            db.add(conflict)
            stored.append(conflict)

        await db.flush()
        logger.info(f"Conflict detection: found {len(stored)} conflict(s)")
        return stored

    except Exception as e:
        logger.warning(f"Conflict detection failed (non-fatal): {e}")
        return []


async def list_conflicts(db: AsyncSession, page: int = 1, limit: int = 50) -> tuple[list[Conflict], int]:
    """Return paginated list of conflicts."""
    from sqlalchemy import func
    count_result = await db.execute(select(func.count()).select_from(Conflict))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Conflict)
        .order_by(Conflict.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return result.scalars().all(), total
