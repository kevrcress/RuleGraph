"""Unit tests for document magic byte validation (app/services/document_service.py)."""
import pytest
from app.services.document_service import _detect_file_type, _is_rejected


# ---------------------------------------------------------------------------
# _detect_file_type
# ---------------------------------------------------------------------------

def test_pdf_detected():
    assert _detect_file_type(b"%PDF-1.4 content here") == "pdf"


def test_docx_detected_pk03():
    assert _detect_file_type(b"PK\x03\x04content") == "docx"


def test_docx_detected_pk05():
    assert _detect_file_type(b"PK\x05\x06content") == "docx"


def test_unknown_returns_none():
    assert _detect_file_type(b"just plain text") is None


def test_empty_bytes_returns_none():
    assert _detect_file_type(b"") is None


def test_partial_magic_no_false_positive():
    # Only one byte of the PDF magic — shouldn't match
    assert _detect_file_type(b"%other-content") is None


# ---------------------------------------------------------------------------
# _is_rejected
# ---------------------------------------------------------------------------

def test_exe_rejected():
    assert _is_rejected(b"MZ\x90\x00\x03") is True


def test_elf_rejected():
    assert _is_rejected(b"\x7fELF\x02\x01") is True


def test_macho_rejected():
    assert _is_rejected(b"\xca\xfe\xba\xbe\x00") is True


def test_pdf_not_rejected():
    assert _is_rejected(b"%PDF-1.4") is False


def test_plain_text_not_rejected():
    assert _is_rejected(b"Hello, world!") is False


def test_empty_bytes_not_rejected():
    assert _is_rejected(b"") is False
