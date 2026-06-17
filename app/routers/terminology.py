"""Terminology router."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services import terminology_service
from app.schemas.terminology import (
    PaginatedTerminology,
    TerminologyDefinitionUpdate,
    TerminologyOut,
)

router = APIRouter(prefix="/terminology", tags=["terminology"])


@router.get("", response_model=PaginatedTerminology)
async def list_terminology(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=200, ge=1, le=500),
    issues_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated terminology. Without issues_only, returns the full glossary."""
    if issues_only:
        items, total = await terminology_service.list_inconsistencies(db, page=page, limit=limit)
    else:
        items, total = await terminology_service.list_all_terms(db, page=page, limit=limit)
    return PaginatedTerminology(
        items=[TerminologyOut.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/rescan", response_model=dict)
async def rescan_terminology(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Re-scan all stored rules for terminology patterns and update the glossary."""
    result = await terminology_service.rescan_all(db)
    await db.commit()
    return result


@router.post("/{term_id}/infer", response_model=TerminologyOut)
async def infer_definition(
    term_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Trigger (or re-trigger) AI definition inference for a term."""
    try:
        inc = await terminology_service.infer_and_save(db, term_id)
        await db.commit()
        return TerminologyOut.model_validate(inc)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Inference failed: {e}")


@router.patch("/{term_id}", response_model=TerminologyOut)
async def update_definition(
    term_id: uuid.UUID,
    body: TerminologyDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Accept or edit the definition for a term."""
    try:
        inc = await terminology_service.update_definition(
            db,
            term_id,
            definition=body.definition,
            definition_status=body.definition_status,
        )
        await db.commit()
        return TerminologyOut.model_validate(inc)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
