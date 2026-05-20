"""Rule lifecycle state machine and authoring assists per Section 17."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatusEnum, RuleVersion
from app.schemas.rule import AuthoringAssist
from app.services.auth_service import write_audit

logger = logging.getLogger(__name__)

# Significant terms used for quick similarity checks
_COMMON_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would could should "
    "may might shall can need to of in on at for with by from that this and or but not".split()
)


def _keywords(text: str) -> set[str]:
    words = text.lower().split()
    return {w.strip(".,;:!?()[]{}\"'") for w in words if w not in _COMMON_WORDS and len(w) > 2}


async def _authoring_assists(
    db: AsyncSession, title: str, definition: str, exclude_id: Optional[uuid.UUID] = None
) -> list[AuthoringAssist]:
    hints: list[AuthoringAssist] = []
    new_kw = _keywords(title + " " + definition)

    q = select(Rule).where(Rule.status != RuleStatusEnum.deprecated)
    if exclude_id is not None:
        q = q.where(Rule.id != exclude_id)
    result = await db.execute(q)
    existing: list[Rule] = list(result.scalars().all())

    for rule in existing:
        existing_kw = _keywords(rule.title + " " + rule.definition)
        overlap = new_kw & existing_kw
        if len(overlap) >= 3:
            hints.append(AuthoringAssist(
                type="similarity",
                message=f"This looks similar to '{rule.title}'. Did you mean to extend or replace it?",
                related_rule_id=rule.id,
            ))
            break  # one hint is enough

    # Completeness: check for undefined referenced terms (simple heuristic)
    quoted = [w for w in definition.split() if w.startswith('"') or w.startswith("'")]
    if quoted:
        hints.append(AuthoringAssist(
            type="completeness",
            message="This rule references quoted terms — ensure they are defined in the graph.",
        ))

    return hints


async def propose_rule(
    db: AsyncSession,
    title: str,
    definition: str,
    owner_id: Optional[uuid.UUID],
    source_type: str = "chat",
    ip_address: Optional[str] = None,
) -> tuple[Rule, list[AuthoringAssist]]:
    rule = Rule(
        title=title,
        definition=definition,
        owner_id=owner_id,
        status=RuleStatusEnum.proposed,
        source_type=source_type,
    )
    db.add(rule)
    await db.flush()

    version = RuleVersion(
        rule_id=rule.id,
        definition=definition,
        status=RuleStatusEnum.proposed,
        changed_by=owner_id,
        change_note="Initial proposal",
    )
    db.add(version)
    await db.flush()

    await write_audit(
        db, "rule.proposed",
        user_id=owner_id,
        target_type="rule",
        target_id=rule.id,
        ip_address=ip_address,
    )

    assists = await _authoring_assists(db, title, definition, exclude_id=rule.id)
    await db.commit()
    await db.refresh(rule)
    return rule, assists


async def update_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    updater_id: uuid.UUID,
    title: Optional[str] = None,
    definition: Optional[str] = None,
    status: Optional[RuleStatusEnum] = None,
    change_note: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule: Optional[Rule] = result.scalar_one_or_none()
    if rule is None:
        raise ValueError(f"Rule {rule_id} not found")

    if title is not None:
        rule.title = title
    if definition is not None:
        rule.definition = definition
    if status is not None:
        rule.status = status
        if status == RuleStatusEnum.deprecated:
            rule.deprecated_at = datetime.now(timezone.utc)
    rule.updated_at = datetime.now(timezone.utc)

    version = RuleVersion(
        rule_id=rule.id,
        definition=rule.definition,
        status=rule.status,
        changed_by=updater_id,
        change_note=change_note or "Updated",
    )
    db.add(version)
    await db.commit()
    await db.refresh(rule)
    return rule


async def approve_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    approver_id: uuid.UUID,
    ip_address: Optional[str] = None,
) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule: Optional[Rule] = result.scalar_one_or_none()
    if rule is None:
        raise ValueError(f"Rule {rule_id} not found")

    rule.status = RuleStatusEnum.approved
    rule.updated_at = datetime.now(timezone.utc)

    version = RuleVersion(
        rule_id=rule.id,
        definition=rule.definition,
        status=RuleStatusEnum.approved,
        changed_by=approver_id,
        change_note="Approved by Business Admin",
    )
    db.add(version)
    await write_audit(
        db, "rule.approved",
        user_id=approver_id,
        target_type="rule",
        target_id=rule.id,
        ip_address=ip_address,
    )
    await db.refresh(rule)
    return rule


async def reject_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    rejector_id: uuid.UUID,
    rejection_note: str,
    ip_address: Optional[str] = None,
) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule: Optional[Rule] = result.scalar_one_or_none()
    if rule is None:
        raise ValueError(f"Rule {rule_id} not found")

    rule.status = RuleStatusEnum.proposed
    rule.updated_at = datetime.now(timezone.utc)

    version = RuleVersion(
        rule_id=rule.id,
        definition=rule.definition,
        status=RuleStatusEnum.proposed,
        changed_by=rejector_id,
        change_note="Rejected — returned to author",
        rejection_note=rejection_note,
    )
    db.add(version)
    await write_audit(
        db, "rule.rejected",
        user_id=rejector_id,
        target_type="rule",
        target_id=rule.id,
        detail={"rejection_note": rejection_note},
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def deprecate_rule(
    db: AsyncSession,
    rule_id: uuid.UUID,
    actor_id: uuid.UUID,
    ip_address: Optional[str] = None,
) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule: Optional[Rule] = result.scalar_one_or_none()
    if rule is None:
        raise ValueError(f"Rule {rule_id} not found")

    rule.status = RuleStatusEnum.deprecated
    rule.deprecated_at = datetime.now(timezone.utc)
    rule.updated_at = datetime.now(timezone.utc)

    version = RuleVersion(
        rule_id=rule.id,
        definition=rule.definition,
        status=RuleStatusEnum.deprecated,
        changed_by=actor_id,
        change_note="Deprecated — Will Not Implement",
    )
    db.add(version)
    await write_audit(
        db, "rule.deprecated",
        user_id=actor_id,
        target_type="rule",
        target_id=rule.id,
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def mark_active(
    db: AsyncSession,
    rule_id: uuid.UUID,
    actor_id: uuid.UUID,
    ip_address: Optional[str] = None,
) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule: Optional[Rule] = result.scalar_one_or_none()
    if rule is None:
        raise ValueError(f"Rule {rule_id} not found")

    rule.status = RuleStatusEnum.active
    rule.updated_at = datetime.now(timezone.utc)

    version = RuleVersion(
        rule_id=rule.id,
        definition=rule.definition,
        status=RuleStatusEnum.active,
        changed_by=actor_id,
        change_note="Promoted to Active — no code change required",
    )
    db.add(version)
    await write_audit(
        db, "rule.promoted_to_active",
        user_id=actor_id,
        target_type="rule",
        target_id=rule.id,
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(rule)
    return rule


async def get_lineage(
    db: AsyncSession,
    rule_id: uuid.UUID,
    since: Optional[datetime] = None,
) -> list[RuleVersion]:
    q = select(RuleVersion).where(RuleVersion.rule_id == rule_id)
    if since:
        q = q.where(RuleVersion.changed_at >= since)
    q = q.order_by(RuleVersion.changed_at.asc())
    result = await db.execute(q)
    return list(result.scalars().all())
