"""
eShop seed — ingests Order.cs and PaymentsProcessor.cs as multi-source eShop data.
Also generates the late_fee_spec_sample.pdf for document upload tests.

Usage:
  # Run standalone (against a live API server):
  python seeds/eshop_seed.py

  # Used by conftest._auto_seed_stage2 fixture (ASGI test client):
  from seeds.eshop_seed import seed_test_data
  await seed_test_data(client)
"""
import asyncio
import io
import logging
import os
import struct
import sys

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF generation — minimal valid PDF with embedded text
# ---------------------------------------------------------------------------

def _build_pdf(text: str) -> bytes:
    """
    Build a minimal but valid PDF containing the given text.
    Uses only stdlib — no external PDF library required.
    """
    # Sanitise text for PDF stream (escape parentheses, backslashes)
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Build individual objects as byte strings
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R\n"
        b"   /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R\n"
        b"   /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>\n"
        b">>\nendobj\n"
    )

    # Content stream — plain text rendered on page
    lines = []
    y = 700
    for line in text.splitlines()[:40]:  # limit to first 40 lines
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        lines.append(f"BT /F1 10 Tf 50 {y} Td ({safe_line}) Tj ET")
        y -= 14
        if y < 50:
            break

    stream_content = "\n".join(lines).encode("latin-1", errors="replace")
    stream_len = len(stream_content)
    obj4 = (
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode()
        + stream_content
        + b"\nendstream\nendobj\n"
    )

    # Assemble body
    header = b"%PDF-1.4\n"
    body = header + obj1 + obj2 + obj3 + obj4

    # Cross-reference table
    xref_pos = len(body)
    offsets = []
    pos = len(header)
    for obj in (obj1, obj2, obj3, obj4):
        offsets.append(pos)
        pos += len(obj)

    xref = b"xref\n0 5\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = (
        f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )

    return body + xref + trailer


def generate_late_fee_pdf(path: str = "seeds/late_fee_spec_sample.pdf") -> None:
    """Generate a minimal valid PDF containing late fee policy text."""
    text = """\
Late Fee Policy Specification v2.1
===================================

1. Grace Period Definition
   Customers have a grace period after the payment due date before a late fee is applied.
   Standard accounts: 7 days grace period.
   Premium accounts: 14 days extended grace period.

2. Late Fee Calculation
   Late fee rate: 1.5% of the outstanding balance per day overdue after the grace period.
   Maximum late fee cap: 25% of the original invoice amount.
   Late fees are calculated on a daily basis starting from day 1 after the grace period expires.

3. Payment Cancellation Window
   Payments may be cancelled within the grace period without incurring fees.
   Cancellation is not permitted once stock confirmation has been acknowledged.

4. Customer Eligibility
   All account types are subject to late fee policies.
   Premium accounts receive extended grace period as a loyalty benefit.
   Accounts in arrears for more than 90 days are escalated to collections.

5. Stock Confirmation Rule
   Payment processing requires confirmation that stock is available.
   Stock availability must be validated before payment authorization proceeds.
   Double-validation of stock across services should be reconciled.

6. Buyer and Customer Terminology
   The term 'buyer' is used in the ordering service to identify the purchasing party.
   The term 'customer' is used in the payments service for the same entity.
   A shared canonical term 'customer_id' is recommended for future consistency.
"""
    pdf_bytes = _build_pdf(text)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"Generated {path} ({len(pdf_bytes)} bytes)")


# ---------------------------------------------------------------------------
# Seed function — called by conftest._auto_seed_stage2
# ---------------------------------------------------------------------------

async def seed_test_data(client) -> None:
    """
    Ingest eShop seed files and generate test artifacts via the ASGI test client.
    Called from conftest._auto_seed_stage2 before Stage 2 tests run.
    """
    # 1. Ingest Order.cs as the 'ordering' service
    if os.path.exists("seeds/Order.cs"):
        with open("seeds/Order.cs", "rb") as f:
            r = await client.post(
                "/ingest/file",
                files={"file": ("Order.cs", f, "text/plain")},
                params={"source_name": "ordering"},
            )
        logger.info(f"Ingested Order.cs: status={r.status_code}")
    else:
        logger.warning("seeds/Order.cs not found — skipping ordering service ingest")

    # 2. Ingest PaymentsProcessor.cs as the 'payments' service
    if os.path.exists("seeds/PaymentsProcessor.cs"):
        with open("seeds/PaymentsProcessor.cs", "rb") as f:
            r = await client.post(
                "/ingest/file",
                files={"file": ("PaymentsProcessor.cs", f, "text/plain")},
                params={"source_name": "payments"},
            )
        logger.info(f"Ingested PaymentsProcessor.cs: status={r.status_code}")
    else:
        logger.warning("seeds/PaymentsProcessor.cs not found — skipping payments service ingest")

    # 3. Generate late_fee_spec_sample.pdf
    try:
        generate_late_fee_pdf("seeds/late_fee_spec_sample.pdf")
    except Exception as e:
        logger.warning(f"Failed to generate late_fee_spec_sample.pdf: {e}")


# ---------------------------------------------------------------------------
# Standalone runner — against a live API server
# ---------------------------------------------------------------------------

async def _seed_standalone() -> None:
    """Run seed against a live server at http://localhost:8000."""
    import httpx

    logging.basicConfig(level=logging.INFO)
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        await seed_test_data(client)

    print("\n[eshop_seed] Seed complete.")
    print("  Check results:")
    print("  curl http://localhost:8000/conflicts | python -m json.tool")
    print("  curl http://localhost:8000/terminology | python -m json.tool")
    print("  curl http://localhost:8000/coverage | python -m json.tool")


if __name__ == "__main__":
    asyncio.run(_seed_standalone())
