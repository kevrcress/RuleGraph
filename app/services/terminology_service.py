"""
Terminology service — detects and stores cross-service naming inconsistencies.

Uses terminology_scanner to extract ID field names from source content,
then groups them by synonym group and flags cross-service variants.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminology import TerminologyInconsistency
from app.ingest.terminology_scanner import (
    extract_id_terms,
    get_id_root,
    find_synonym_group,
)

logger = logging.getLogger(__name__)


async def scan_content_and_update(
    db: AsyncSession,
    content: str,
    service_name: str,
) -> None:
    """
    Scan source content for ID field names and update terminology_inconsistencies.
    Called after each file is ingested.
    """
    try:
        new_terms = extract_id_terms(content)
        if not new_terms:
            return

        # Load all existing inconsistency records
        result = await db.execute(select(TerminologyInconsistency))
        existing: list[TerminologyInconsistency] = list(result.scalars().all())

        newly_created: list[TerminologyInconsistency] = []

        for term in new_terms:
            root = get_id_root(term)
            synonym_group = find_synonym_group(root)
            if synonym_group is None:
                continue

            matched: TerminologyInconsistency | None = None
            same_service_record: TerminologyInconsistency | None = None

            for inc in existing:
                group_roots = {get_id_root(v) for v in inc.variants}
                group_in_same = any(find_synonym_group(r) == synonym_group for r in group_roots)
                if not group_in_same:
                    continue
                if service_name in inc.services:
                    same_service_record = inc
                else:
                    matched = inc

            if matched is not None:
                if term not in matched.variants:
                    matched.variants = list(matched.variants) + [term]
                if service_name not in matched.services:
                    matched.services = list(matched.services) + [service_name]
            elif same_service_record is not None:
                if term not in same_service_record.variants:
                    same_service_record.variants = list(same_service_record.variants) + [term]
            else:
                new_inc = TerminologyInconsistency(
                    id=uuid.uuid4(),
                    canonical_term=None,
                    variants=[term],
                    services=[service_name],
                )
                db.add(new_inc)
                existing.append(new_inc)
                newly_created.append(new_inc)

        await db.flush()

        # Auto-infer definitions for brand-new records (best-effort, non-fatal)
        for inc in newly_created:
            await _try_infer_definition(db, inc)

    except Exception as e:
        logger.warning(f"Terminology scan failed for {service_name!r} (non-fatal): {e}")


async def _try_infer_definition(
    db: AsyncSession,
    inc: TerminologyInconsistency,
) -> None:
    from app.services.definition_service import infer_definition

    if inc.definition:
        return
    try:
        term = inc.canonical_term or inc.variants[0]
        definition, confidence = await infer_definition(term, inc.variants, inc.services, db=db)
        inc.definition = definition
        inc.definition_confidence = confidence
        inc.definition_status = "draft"
        await db.flush()
    except Exception as e:
        logger.warning(f"Definition inference failed for term {inc.id} (non-fatal): {e}")


async def infer_and_save(
    db: AsyncSession,
    term_id: uuid.UUID,
) -> TerminologyInconsistency:
    """Force-infer (or re-infer) a definition for the given term. Returns updated record."""
    from app.services.definition_service import infer_definition

    result = await db.execute(
        select(TerminologyInconsistency).where(TerminologyInconsistency.id == term_id)
    )
    inc = result.scalar_one_or_none()
    if inc is None:
        raise ValueError(f"Term {term_id} not found")

    term = inc.canonical_term or (inc.variants[0] if inc.variants else str(term_id))
    definition, confidence = await infer_definition(term, inc.variants, inc.services, db=db)
    inc.definition = definition
    inc.definition_confidence = confidence
    inc.definition_status = "draft"
    await db.flush()
    return inc


async def update_definition(
    db: AsyncSession,
    term_id: uuid.UUID,
    definition: str | None,
    definition_status: str | None,
) -> TerminologyInconsistency:
    """Apply a user-supplied definition or status change."""
    result = await db.execute(
        select(TerminologyInconsistency).where(TerminologyInconsistency.id == term_id)
    )
    inc = result.scalar_one_or_none()
    if inc is None:
        raise ValueError(f"Term {term_id} not found")

    if definition is not None:
        inc.definition = definition
        # If the user edited the text, mark as edited unless they explicitly set a status
        if definition_status is None:
            inc.definition_status = "edited"
    if definition_status is not None:
        inc.definition_status = definition_status

    await db.flush()
    return inc


async def rescan_all(db: AsyncSession) -> dict:
    """Re-run the terminology scanner over all stored rules, grouped by service.

    Additive — existing records are preserved. Returns a summary dict.
    """
    from sqlalchemy import func
    from app.models.rule import Rule, RuleService, Service

    count_before_result = await db.execute(
        select(func.count()).select_from(TerminologyInconsistency)
    )
    count_before = count_before_result.scalar_one()

    rows_result = await db.execute(
        select(Rule.title, Rule.definition, Service.name)
        .join(RuleService, Rule.id == RuleService.rule_id)
        .join(Service, RuleService.service_id == Service.id)
    )
    rows = rows_result.all()

    service_chunks: dict[str, list[str]] = {}
    for title, definition, service_name in rows:
        service_chunks.setdefault(service_name, []).append(f"{title}\n{definition}")

    for service_name, chunks in service_chunks.items():
        combined = "\n\n".join(chunks)
        await scan_content_and_update(db, combined, service_name)

    count_after_result = await db.execute(
        select(func.count()).select_from(TerminologyInconsistency)
    )
    count_after = count_after_result.scalar_one()

    return {
        "services_scanned": len(service_chunks),
        "terms_before": count_before,
        "terms_after": count_after,
        "terms_added": count_after - count_before,
    }


async def list_inconsistencies(
    db: AsyncSession, page: int = 1, limit: int = 50
) -> tuple[list[TerminologyInconsistency], int]:
    """Return paginated terminology inconsistencies that involve 2+ services."""
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count())
        .select_from(TerminologyInconsistency)
        .where(func.array_length(TerminologyInconsistency.services, 1) >= 2)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(TerminologyInconsistency)
        .where(func.array_length(TerminologyInconsistency.services, 1) >= 2)
        .order_by(TerminologyInconsistency.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def list_all_terms(
    db: AsyncSession, page: int = 1, limit: int = 200
) -> tuple[list[TerminologyInconsistency], int]:
    """Return all terminology records for the glossary view, sorted alphabetically."""
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count()).select_from(TerminologyInconsistency)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(TerminologyInconsistency)
        .order_by(
            TerminologyInconsistency.canonical_term.asc().nullsfirst(),
            TerminologyInconsistency.created_at.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total
