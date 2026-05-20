"""
Document service — upload handling, magic byte validation, sandbox storage,
and document preview (extraction without committing).

Allowed types (validated by magic bytes):
  PDF   — starts with %PDF
  DOCX  — starts with PK\x03\x04 (ZIP)
  TXT   — any content (no binary magic bytes)
  MD    — any content (no binary magic bytes)

Rejected types:
  EXE/DLL — starts with MZ (Windows PE)
  ELF     — starts with \x7fELF (Linux executable)
"""
import logging
import os
import uuid
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.document import Document

logger = logging.getLogger(__name__)

UPLOADS_DIR = "uploads"

# Magic bytes → file type
MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"%PDF", "pdf"),
    (b"PK\x03\x04", "docx"),
    (b"PK\x05\x06", "docx"),
]

# Rejected signatures — executable formats
REJECTED_MAGIC: list[bytes] = [
    b"MZ",         # Windows PE (EXE, DLL)
    b"\x7fELF",    # Linux ELF executable
    b"\xca\xfe\xba\xbe",  # Mach-O universal binary
]

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".eml", ".msg"}


def _detect_file_type(header: bytes) -> Optional[str]:
    """Detect file type from magic bytes. Returns type string or None if unknown."""
    for magic, ftype in MAGIC_BYTES:
        if header.startswith(magic):
            return ftype
    return None


def _is_rejected(header: bytes) -> bool:
    """Return True if magic bytes indicate a disallowed binary type."""
    return any(header.startswith(m) for m in REJECTED_MAGIC)


def _extract_text_from_pdf(content: bytes) -> str:
    """
    Extract plain text from a PDF byte stream.
    Phase 1: scan for text objects in the PDF content stream.
    Looks for BT...ET blocks and extracts parenthesized strings.
    """
    import re
    text_parts = []
    # Try to decode entire content as text first (handles text-based PDFs)
    try:
        decoded = content.decode("latin-1", errors="replace")
    except Exception:
        decoded = ""

    # Extract text from BT...ET blocks (PDF text objects)
    bt_blocks = re.findall(r'BT\s*(.*?)\s*ET', decoded, re.DOTALL)
    for block in bt_blocks:
        strings = re.findall(r'\(([^)]*)\)', block)
        text_parts.extend(s for s in strings if s.strip())

    if text_parts:
        return " ".join(text_parts)

    # Fallback: extract any parenthesized strings that look like text
    all_strings = re.findall(r'\(([A-Za-z][^)]{3,})\)', decoded)
    return " ".join(all_strings[:200])


async def validate_and_store(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    owner_id: Optional[uuid.UUID] = None,
    tags: Optional[list[str]] = None,
) -> Document:
    """
    Validate file type via magic bytes, reject disallowed types,
    store approved files in sandbox.

    Raises:
        ValueError: if the file type is not allowed.
    """
    header = file_bytes[:8]

    if _is_rejected(header):
        raise ValueError(
            f"File type not allowed: magic bytes indicate executable/binary format. "
            f"Allowed types: PDF, DOCX, TXT, MD, EML, MSG."
        )

    # Determine extension
    _, ext = os.path.splitext(filename.lower())

    # For text files (TXT, MD, EML, MSG) we skip magic byte check
    if ext in {".txt", ".md", ".eml", ".msg"}:
        file_type = ext.lstrip(".")
    else:
        detected = _detect_file_type(header)
        if detected is None and ext in {".pdf", ".docx"}:
            raise ValueError(
                f"File '{filename}' has extension '{ext}' but magic bytes do not match. "
                f"File rejected for safety."
            )
        file_type = detected or ext.lstrip(".")

    # Store file to uploads directory
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    storage_filename = f"{file_id}{ext or '.bin'}"
    storage_path = os.path.join(UPLOADS_DIR, storage_filename)
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    doc = Document(
        id=file_id,
        filename=filename,
        file_type=file_type,
        storage_path=storage_path,
        status="sandbox",
        owner_id=owner_id,
        tags=tags or [],
    )
    db.add(doc)
    await db.flush()
    return doc


async def preview_document(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from a document and run the extraction pipeline
    to produce proposed changes WITHOUT committing anything to the DB.
    """
    header = file_bytes[:8]

    if _is_rejected(header):
        raise ValueError("File type not allowed for preview.")

    # Extract text
    _, ext = os.path.splitext(filename.lower())
    if ext == ".pdf":
        text = _extract_text_from_pdf(file_bytes)
    else:
        try:
            text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = file_bytes.decode("latin-1", errors="replace")

    if not text.strip():
        return {
            "proposed_new_rules": [],
            "proposed_rule_changes": [],
            "context_additions": [],
            "conflicts_detected": [],
            "document_stored_as": "sandbox",
        }

    # Run extraction pipeline on the text (without storing rules)
    try:
        from app.ingest.complexity import score_complexity
        from app.ingest.extractor import extract_rules

        complexity = score_complexity(text)
        result = await extract_rules(text, complexity)
        proposed = [
            {
                "title": r.title,
                "definition": r.definition,
                "confidence": r.confidence,
            }
            for r in (result.rules if result and not result.error else [])
        ]
    except Exception as e:
        logger.warning(f"Document preview extraction failed (non-fatal): {e}")
        proposed = []

    return {
        "proposed_new_rules": proposed,
        "proposed_rule_changes": [],
        "context_additions": [],
        "conflicts_detected": [],
        "document_stored_as": "sandbox",
    }


async def list_documents(
    db: AsyncSession, page: int = 1, limit: int = 50
) -> tuple[list[Document], int]:
    """Return paginated list of documents."""
    count_result = await db.execute(select(func.count()).select_from(Document))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Document)
        .order_by(Document.uploaded_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total
