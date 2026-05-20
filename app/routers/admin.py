"""
Admin router — user management, review queue, TL dashboard, audit log,
ingest errors, system settings, and synonym management.
All endpoints require JWT auth and appropriate roles.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.audit import AuditLog
from app.models.ingest import IngestError
from app.models.rule import Rule, RuleStatusEnum
from app.models.settings import SystemSetting
from app.models.user import User
from app.schemas.ingest import IngestErrorItem, PaginatedIngestErrors
from app.schemas.rule import RejectRequest, WorkItemRequest, RuleDetail
from app.schemas.user import AdminUserCreate, AdminUserUpdate, PaginatedUsers, UserResponse
from app.services import rule_service
from app.services.auth_service import write_audit
from app.services.workitem_service import create_work_item
import bcrypt as _bcrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _hash_pw(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

# ──────────────────────────────────────────────────────────────────────────────
# Ingest errors
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/ingest-errors", response_model=PaginatedIngestErrors)
async def list_ingest_errors(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    offset = (page - 1) * limit
    count_result = await db.execute(select(func.count()).select_from(IngestError))
    total = count_result.scalar_one()
    items_result = await db.execute(
        select(IngestError).order_by(IngestError.created_at.desc()).offset(offset).limit(limit)
    )
    errors = items_result.scalars().all()
    return PaginatedIngestErrors(items=[IngestErrorItem.model_validate(e) for e in errors], total=total)


@router.put("/ingest-errors/{error_id}/resolve")
async def resolve_ingest_error(
    error_id: uuid.UUID,
    resolution_note: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    result = await db.execute(select(IngestError).where(IngestError.id == error_id))
    error = result.scalar_one_or_none()
    if error is None:
        raise HTTPException(status_code=404, detail="Ingest error not found")
    from datetime import timezone
    error.resolved_at = datetime.now(timezone.utc)
    error.resolved_by = uuid.UUID(current_user["sub"])
    error.resolution_note = resolution_note
    await db.commit()
    return {"status": "resolved"}


# ──────────────────────────────────────────────────────────────────────────────
# Audit log
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def list_audit_log(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    action: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    offset = (page - 1) * limit
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.where(AuditLog.action == action)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()
    items = (await db.execute(q.offset(offset).limit(limit))).scalars().all()

    return {
        "items": [
            {
                "id": str(e.id),
                "action": e.action,
                "user_id": str(e.user_id) if e.user_id else None,
                "target_type": e.target_type,
                "target_id": str(e.target_id) if e.target_id else None,
                "detail": e.detail,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


# ──────────────────────────────────────────────────────────────────────────────
# User management
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    offset = (page - 1) * limit
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    users = (
        await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))
    ).scalars().all()
    return PaginatedUsers(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    existing = (await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(
        username=body.username,
        email=body.email,
        name=body.name,
        password_hash=_hash_pw(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()
    await write_audit(db, "user.created", user_id=uuid.UUID(current_user["sub"]),
                      target_type="user", target_id=user.id)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email
    if body.name is not None:
        user.name = body.name
    if body.role is not None:
        user.role = body.role
    if body.password is not None:
        user.password_hash = _hash_pw(body.password)

    if body.role is not None and body.role != old_role:
        await write_audit(db, "user.role_changed", user_id=uuid.UUID(current_user["sub"]),
                          target_type="user", target_id=user.id,
                          detail={"old_role": old_role, "new_role": body.role})
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ──────────────────────────────────────────────────────────────────────────────
# Review queue (BA + Admin)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/review-queue")
async def get_review_queue(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("business_admin", "admin")),
):
    offset = (page - 1) * limit
    q = select(Rule).where(Rule.status == RuleStatusEnum.proposed)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rules = (await db.execute(q.order_by(Rule.created_at.asc()).offset(offset).limit(limit))).scalars().all()
    return {
        "items": [RuleDetail.model_validate(r).model_dump() for r in rules],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.put("/review-queue/{rule_id}/approve")
async def approve_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("business_admin", "admin")),
):
    approver_id = uuid.UUID(current_user["sub"])
    try:
        rule = await rule_service.approve_rule(db, rule_id, approver_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RuleDetail.model_validate(rule).model_dump()


@router.put("/review-queue/{rule_id}/reject")
async def reject_rule(
    rule_id: uuid.UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("business_admin", "admin")),
):
    rejector_id = uuid.UUID(current_user["sub"])
    try:
        rule = await rule_service.reject_rule(db, rule_id, rejector_id, body.rejection_note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RuleDetail.model_validate(rule).model_dump()


@router.put("/review-queue/{rule_id}/deprecate")
async def deprecate_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("business_admin", "admin")),
):
    actor_id = uuid.UUID(current_user["sub"])
    try:
        rule = await rule_service.deprecate_rule(db, rule_id, actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RuleDetail.model_validate(rule).model_dump()


# ──────────────────────────────────────────────────────────────────────────────
# Tech Lead dashboard (TL + Admin)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/tech-lead-dashboard")
async def get_tl_dashboard(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    offset = (page - 1) * limit
    q = select(Rule).where(Rule.status == RuleStatusEnum.approved)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rules = (await db.execute(q.order_by(Rule.updated_at.asc()).offset(offset).limit(limit))).scalars().all()
    return {
        "items": [RuleDetail.model_validate(r).model_dump() for r in rules],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.put("/tech-lead-dashboard/{rule_id}/code-change")
async def flag_code_change(
    rule_id: uuid.UUID,
    body: WorkItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    actor_id = uuid.UUID(current_user["sub"])

    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Fetch TL's connected accounts for work item creation
    from app.models.user import ConnectedAccount
    accounts_result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == actor_id)
    )
    accounts = accounts_result.scalars().all()

    workitem_id, workitem_url = await create_work_item(
        rule_id=rule_id,
        title=body.workitem_title,
        body=body.workitem_body,
        repo=body.repo,
        project=body.project,
        connected_accounts=accounts,
    )

    from datetime import timezone
    rule.workitem_id = workitem_id
    rule.workitem_url = workitem_url
    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()

    await write_audit(
        db, "workitem.created",
        user_id=actor_id,
        target_type="rule",
        target_id=rule.id,
        detail={"workitem_id": workitem_id, "workitem_url": workitem_url},
    )
    await db.commit()
    await db.refresh(rule)
    return RuleDetail.model_validate(rule).model_dump()


@router.put("/tech-lead-dashboard/{rule_id}/no-code")
async def flag_no_code(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    actor_id = uuid.UUID(current_user["sub"])
    try:
        rule = await rule_service.mark_active(db, rule_id, actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RuleDetail.model_validate(rule).model_dump()


# ──────────────────────────────────────────────────────────────────────────────
# System settings (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    settings_result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return {"settings": {s.key: s.value for s in settings_result.scalars().all()}}


@router.put("/settings")
async def update_settings(
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    actor_id = uuid.UUID(current_user["sub"])
    for key, value in updates.items():
        existing = (await db.execute(select(SystemSetting).where(SystemSetting.key == key))).scalar_one_or_none()
        if existing:
            existing.value = str(value)
            existing.updated_by = actor_id
        else:
            db.add(SystemSetting(key=key, value=str(value), updated_by=actor_id))
    await write_audit(db, "admin.settings_changed", user_id=actor_id, detail=updates)
    await db.commit()
    return {"status": "updated"}


# ──────────────────────────────────────────────────────────────────────────────
# Synonym management (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/synonyms")
async def list_synonyms(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    from app.models.terminology import TerminologyInconsistency
    result = await db.execute(
        select(TerminologyInconsistency).order_by(TerminologyInconsistency.detected_at.desc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(t.id),
                "canonical_term": t.canonical_term,
                "variants": t.variants,
                "services": t.services,
                "status": t.status,
                "detected_at": t.detected_at.isoformat() if t.detected_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ]
    }


@router.put("/synonyms/{synonym_id}/approve")
async def approve_synonym(
    synonym_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    from app.models.terminology import TerminologyInconsistency
    item = (await db.execute(
        select(TerminologyInconsistency).where(TerminologyInconsistency.id == synonym_id)
    )).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Synonym not found")
    item.status = "approved"
    await write_audit(db, "synonym.approved", user_id=uuid.UUID(current_user["sub"]),
                      target_type="terminology", target_id=synonym_id)
    await db.commit()
    return {"status": "approved"}


@router.put("/synonyms/{synonym_id}/reject")
async def reject_synonym(
    synonym_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    from app.models.terminology import TerminologyInconsistency
    item = (await db.execute(
        select(TerminologyInconsistency).where(TerminologyInconsistency.id == synonym_id)
    )).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Synonym not found")
    item.status = "rejected"
    await write_audit(db, "synonym.rejected", user_id=uuid.UUID(current_user["sub"]),
                      target_type="terminology", target_id=synonym_id)
    await db.commit()
    return {"status": "rejected"}


# ──────────────────────────────────────────────────────────────────────────────
# Data reset
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/data")
async def clear_all_data(
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    """
    Delete all ingested graph data: rules, services, conflicts, terminology,
    feedback, documents, ingest runs, and ingest errors.

    Preserves: users, connected accounts, audit log, system settings.

    Requires ?confirm=true to execute. Without it, returns a preview of
    what would be deleted.
    """
    from sqlalchemy import text
    from app.models.rule import Rule, RuleVersion, Service, RuleService
    from app.models.document import Document, RuleDocument
    from app.models.conflict import Conflict
    from app.models.terminology import TerminologyInconsistency
    from app.models.feedback import Feedback
    from app.models.ingest import IngestRun, IngestError
    from app.models.notification import Notification, Subscription

    async def _count(model) -> int:
        result = await db.execute(select(func.count()).select_from(model))
        return result.scalar_one()

    counts = {
        "rules": await _count(Rule),
        "rule_versions": await _count(RuleVersion),
        "services": await _count(Service),
        "conflicts": await _count(Conflict),
        "terminology_inconsistencies": await _count(TerminologyInconsistency),
        "feedback": await _count(Feedback),
        "documents": await _count(Document),
        "ingest_runs": await _count(IngestRun),
        "ingest_errors": await _count(IngestError),
        "notifications": await _count(Notification),
        "subscriptions": await _count(Subscription),
    }
    total = sum(counts.values())

    if not confirm:
        return {
            "status": "preview",
            "message": "Add ?confirm=true to actually delete. Users, audit log, and settings are preserved.",
            "would_delete": counts,
            "total_rows": total,
        }

    # Delete in dependency order (children before parents)
    await db.execute(text("DELETE FROM feedback"))
    await db.execute(text("DELETE FROM rule_documents"))
    await db.execute(text("DELETE FROM rule_services"))
    await db.execute(text("DELETE FROM rule_versions"))
    await db.execute(text("DELETE FROM subscriptions"))
    await db.execute(text("DELETE FROM notifications"))
    await db.execute(text("DELETE FROM rules"))
    await db.execute(text("DELETE FROM services"))
    await db.execute(text("DELETE FROM documents"))
    await db.execute(text("DELETE FROM conflicts"))
    await db.execute(text("DELETE FROM terminology_inconsistencies"))
    await db.execute(text("DELETE FROM ingest_errors"))
    await db.execute(text("DELETE FROM ingest_runs"))

    await write_audit(
        db, "admin.data_cleared",
        user_id=uuid.UUID(current_user["sub"]),
        detail={"deleted": counts},
    )
    await db.commit()

    return {
        "status": "cleared",
        "message": "All graph data deleted. Users, audit log, and settings preserved.",
        "deleted": counts,
        "total_rows": total,
    }
