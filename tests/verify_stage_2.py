"""
Stage 2 verification: Multi-source ingest, conflict detection,
terminology, coverage, diff, document upload.
Assumes eshop_seed.py has been run before this test suite.
Run: python seeds/eshop_seed.py && pytest tests/verify_stage_2.py -v
"""
import os
import io
import pytest

EXPECTED_CONFLICT_SERVICES = {"ordering", "payments"}
EXPECTED_TERMINOLOGY_VARIANTS = {"buyerid", "customerid"}


class TestConflictDetection:

    async def test_conflicts_endpoint_returns_200(self, client):
        r = await client.get("/conflicts")
        assert r.status_code == 200

    async def test_at_least_one_conflict_detected(self, client):
        r = await client.get("/conflicts?limit=50")
        conflicts = r.json().get("items", r.json())
        assert len(conflicts) > 0, "Expected at least one conflict after eShop ingest"

    async def test_ordering_payments_conflict_present(self, client):
        r = await client.get("/conflicts?limit=50")
        conflicts = r.json().get("items", r.json())
        found = False
        for c in conflicts:
            services = {s.lower() for s in c.get("services", [])}
            if services & EXPECTED_CONFLICT_SERVICES:
                found = True
                break
        assert found, (
            "Expected a conflict involving Ordering and/or Payments services.\n"
            f"Conflicts found: {[c.get('title') for c in conflicts]}"
        )

    async def test_conflict_has_required_fields(self, client):
        r = await client.get("/conflicts?limit=1")
        items = r.json().get("items", r.json())
        assert len(items) > 0
        c = items[0]
        for field in ["id", "description", "services"]:
            assert field in c, f"Conflict missing field: {field}"


class TestTerminologyDetection:

    async def test_terminology_endpoint_returns_200(self, client):
        r = await client.get("/terminology")
        assert r.status_code == 200

    async def test_at_least_one_terminology_inconsistency(self, client):
        r = await client.get("/terminology?limit=50")
        items = r.json().get("items", r.json())
        assert len(items) > 0, "Expected at least one terminology inconsistency"

    async def test_buyerid_customerid_inconsistency_detected(self, client):
        r = await client.get("/terminology?limit=50")
        items = r.json().get("items", r.json())
        found = False
        for item in items:
            variants = {v.lower().replace("_", "").replace("-", "") for v in item.get("variants", [])}
            if variants & EXPECTED_TERMINOLOGY_VARIANTS:
                found = True
                break
        assert found, (
            "Expected buyerId/customerId terminology inconsistency.\n"
            f"Found: {[i.get('variants') for i in items]}"
        )


class TestCoverageDetection:

    async def test_coverage_endpoint_returns_200(self, client):
        r = await client.get("/coverage")
        assert r.status_code == 200

    async def test_at_least_one_coverage_gap(self, client):
        r = await client.get("/coverage?limit=50")
        items = r.json().get("items", r.json())
        assert len(items) > 0, "Expected at least one coverage gap after eShop ingest"

    async def test_coverage_item_has_status(self, client):
        r = await client.get("/coverage?limit=1")
        items = r.json().get("items", r.json())
        assert len(items) > 0
        item = items[0]
        assert "coverage_status" in item, f"Coverage item missing status: {item}"
        valid = {"covered", "partial", "uncovered", "coverage_gap", "stale"}
        assert item["coverage_status"].lower() in valid


class TestDiffEndpoint:

    async def test_diff_list_returns_200(self, client):
        r = await client.get("/diff?since=2000-01-01")
        assert r.status_code == 200

    async def test_diff_list_is_paginated(self, client):
        r = await client.get("/diff?since=2000-01-01")
        body = r.json()
        assert "items" in body or isinstance(body, list)

    async def test_per_rule_diff_returns_200(self, client):
        r = await client.get("/rules?limit=1")
        rule_id = r.json().get("items", r.json())[0]["id"]
        r2 = await client.get(f"/diff/{rule_id}")
        assert r2.status_code == 200

    async def test_per_rule_diff_has_before_after(self, client):
        r = await client.get("/rules?limit=1")
        rule_id = r.json().get("items", r.json())[0]["id"]
        diff = (await client.get(f"/diff/{rule_id}")).json()
        assert "before" in diff or "versions" in diff, (
            f"Diff response missing before/after data: {diff}"
        )


class TestDocumentUpload:

    async def test_upload_valid_pdf(self, client):
        pdf_bytes = b"%PDF-1.4 fake pdf content for testing"
        r = await client.post(
            "/documents",
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        # Sandbox mode — expect 200 or 201
        assert r.status_code in (200, 201), f"PDF upload failed: {r.text}"

    async def test_upload_invalid_type_rejected(self, client):
        r = await client.post(
            "/documents",
            files={"file": ("malware.exe", io.BytesIO(b"MZ fake exe"), "application/octet-stream")}
        )
        assert r.status_code == 400, "Expected 400 for disallowed file type"

    async def test_documents_preview_returns_preview(self, client):
        if not os.path.exists("seeds/late_fee_spec_sample.pdf"):
            pytest.skip("Sample PDF not present — skipping preview test")
        with open("seeds/late_fee_spec_sample.pdf", "rb") as f:
            r = await client.post(
                "/documents/preview",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        assert r.status_code == 200
        body = r.json()
        assert any(k in body for k in ["proposed_new_rules", "proposed_rule_changes", "context_additions"])

    async def test_documents_library_returns_200(self, client):
        r = await client.get("/documents")
        assert r.status_code == 200
