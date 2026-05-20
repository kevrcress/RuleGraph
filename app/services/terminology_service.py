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

        for term in new_terms:
            root = get_id_root(term)
            synonym_group = find_synonym_group(root)
            if synonym_group is None:
                continue

            # Look for an existing inconsistency record for this synonym group
            # from a DIFFERENT service
            matched: TerminologyInconsistency | None = None
            same_service_record: TerminologyInconsistency | None = None

            for inc in existing:
                # Check if this inconsistency is for the same synonym group
                group_roots = {get_id_root(v) for v in inc.variants}
                group_in_same = any(find_synonym_group(r) == synonym_group for r in group_roots)
                if not group_in_same:
                    continue

                if service_name in inc.services:
                    same_service_record = inc
                else:
                    matched = inc

            if matched is not None:
                # Cross-service match — add this term and service to the existing record
                if term not in matched.variants:
                    matched.variants = list(matched.variants) + [term]
                if service_name not in matched.services:
                    matched.services = list(matched.services) + [service_name]
            elif same_service_record is not None:
                # Same service already in a record — add the new variant to it
                if term not in same_service_record.variants:
                    same_service_record.variants = list(same_service_record.variants) + [term]
            else:
                # No matching record — create a new single-service record
                new_inc = TerminologyInconsistency(
                    id=uuid.uuid4(),
                    canonical_term=None,
                    variants=[term],
                    services=[service_name],
                )
                db.add(new_inc)
                existing.append(new_inc)

        await db.flush()

    except Exception as e:
        logger.warning(f"Terminology scan failed for {service_name!r} (non-fatal): {e}")


async def list_inconsistencies(
    db: AsyncSession, page: int = 1, limit: int = 50
) -> tuple[list[TerminologyInconsistency], int]:
    """Return paginated terminology inconsistencies that involve 2+ services."""
    from sqlalchemy import func

    # Only return records with 2+ services (actual cross-service inconsistencies)
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
