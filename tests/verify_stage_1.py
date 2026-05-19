"""
Stage 1 verification: Foundation.
Tests single-file ingest, rule storage, and basic retrieval.
All tests use the ASGI test client — no running server needed.
"""
import pytest
import pytest_asyncio
import httpx

SEED_RULE_TITLES = [
    "Order Cancellation Window",
    "Stock Confirmation Before Payment",
    "Buyer Identity Match",
]

SEED_CONFIDENCES = {
    "Order Cancellation Window": (0.75, 1.0),
    "Stock Confirmation Before Payment": (0.65, 1.0),
    "Buyer Identity Match": (0.55, 1.0),
}


class TestIngestSingleFile:

    @pytest_asyncio.fixture(autouse=True, scope="class")
    async def ingest_seed(self, client):
        """Ingest Order.cs once for all tests in this class."""
        with open("seeds/Order.cs", "rb") as f:
            r = await client.post("/ingest/file", files={"file": ("Order.cs", f, "text/plain")})
        assert r.status_code == 200, f"Ingest failed: {r.text}"

    async def test_ingest_returns_success(self, client):
        with open("seeds/Order.cs", "rb") as f:
            r = await client.post("/ingest/file", files={"file": ("Order.cs", f, "text/plain")})
        assert r.status_code == 200

    async def test_rules_list_returns_200(self, client):
        r = await client.get("/rules")
        assert r.status_code == 200

    async def test_rules_list_is_paginated(self, client):
        r = await client.get("/rules")
        body = r.json()
        assert "items" in body or isinstance(body, list), "Expected paginated response"

    async def test_seed_rules_extracted(self, client):
        r = await client.get("/rules?limit=50")
        assert r.status_code == 200
        rules = r.json().get("items", r.json())
        titles = [rule["title"] for rule in rules]
        for expected in SEED_RULE_TITLES:
            assert any(expected.lower() in t.lower() for t in titles), (
                f"Expected rule '{expected}' not found in extracted rules.\n"
                f"Found: {titles}"
            )

    async def test_seed_rules_have_confidence_scores(self, client):
        r = await client.get("/rules?limit=50")
        rules = r.json().get("items", r.json())
        for rule in rules:
            assert "extraction_confidence" in rule, f"Rule missing confidence: {rule['title']}"
            assert rule["extraction_confidence"] is not None

    async def test_seed_rule_confidence_in_expected_range(self, client):
        r = await client.get("/rules?limit=50")
        rules = r.json().get("items", r.json())
        rule_map = {rule["title"]: rule for rule in rules}
        for expected_title, (low, high) in SEED_CONFIDENCES.items():
            match = next(
                (r for t, r in rule_map.items() if expected_title.lower() in t.lower()), None
            )
            assert match, f"Rule '{expected_title}' not found"
            conf = match["extraction_confidence"]
            assert low <= conf <= high, (
                f"Rule '{expected_title}' confidence {conf} outside expected range [{low}, {high}]"
            )

    async def test_get_rule_by_id(self, client):
        r = await client.get("/rules?limit=1")
        rules = r.json().get("items", r.json())
        assert len(rules) > 0, "No rules found"
        rule_id = rules[0]["id"]
        r2 = await client.get(f"/rules/{rule_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == rule_id

    async def test_rule_detail_has_required_fields(self, client):
        r = await client.get("/rules?limit=1")
        rule_id = r.json().get("items", r.json())[0]["id"]
        rule = (await client.get(f"/rules/{rule_id}")).json()
        for field in ["id", "title", "definition", "status", "extraction_confidence", "source_type"]:
            assert field in rule, f"Rule missing field: {field}"

    async def test_pagination_limit_respected(self, client):
        r = await client.get("/rules?limit=1")
        assert r.status_code == 200
        body = r.json()
        items = body.get("items", body)
        assert len(items) <= 1

    async def test_ingest_run_recorded(self, client):
        r = await client.get("/admin/ingest-errors")
        assert r.status_code == 200

    async def test_no_ingest_errors_for_clean_seed(self, client):
        r = await client.get("/admin/ingest-errors")
        errors = r.json().get("items", r.json())
        assert len(errors) == 0, (
            f"Expected no ingest errors for clean seed file. Got: {errors}"
        )
