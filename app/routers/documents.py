"""Documents router — POST /documents, POST /documents/preview, GET /documents."""
import logging

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.services import document_service
from app.schemas.document import DocumentOut, PaginatedDocuments, DocumentPreviewResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a document. Validates file type via magic bytes.
    Stores in sandbox — requires Business Admin approval to enter the graph.
    """
    file_bytes = await file.read()
    filename = file.filename or "unknown"
    try:
        doc = await document_service.validate_and_store(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
        )
        return DocumentOut.model_validate(doc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("business_admin", "admin")),
):
    """
    Sandbox preview — extract proposed rule changes without committing.
    Returns proposed_new_rules, proposed_rule_changes, context_additions.
    """
    file_bytes = await file.read()
    filename = file.filename or "unknown"
    try:
        preview = await document_service.preview_document(file_bytes, filename)
        return DocumentPreviewResponse(**preview)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=PaginatedDocuments)
async def list_documents(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated document library."""
    items, total = await document_service.list_documents(db, page=page, limit=limit)
    return PaginatedDocuments(
        items=[DocumentOut.model_validate(d) for d in items],
        total=total,
        page=page,
        limit=limit,
    )
