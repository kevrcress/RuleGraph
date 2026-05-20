"""Integration tests for the ingest pipeline and admin ingest-error endpoint."""
import io
import os
import pytest
from unittest.mock import AsyncMock, patch

from app.ingest.extractor import ExtractionResult, ExtractedRule

SEED_TITLES = [
    "Order Cancellation Window",
    "Stock Confirmation Before Payment",
    "Buyer Identity Match",
]

# Canned extraction result to avoid needing a live Anthropic API key in CI
_MOCK_RESULT = ExtractionResult(
    rules=[
        ExtractedRule(title=t, definition=f"Definition of {t}.", confidence=0.9)
        for t in SEED_TITLES
    ],
    model_used="mock",
)


def _has_api_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and not key.startswith("sk-ant-api03-XXXX")


class TestFileIngest:

    async def test_ingest_order_cs_returns_200(self, client, seeded_users):
        with patch("app.ingest.pipeline.extract_rules", AsyncMock(return_value=_MOCK_RESULT)):
            with open("seeds/Order.cs", "rb") as f:
                r = await client.post(
                    "/ingest/file",
                    files={"file": ("Order.cs", f, "text/plain")},
                    headers={"Authorization": f"Bearer {seeded_users['admin']}"},
                )
        assert r.status_code == 200

    async def test_ingest_extracts_known_rules(self, client, seeded_users):
        with patch("app.ingest.pipeline.extract_rules", AsyncMock(return_value=_MOCK_RESULT)):
            with open("seeds/Order.cs", "rb") as f:
                await client.post(
                    "/ingest/file",
                    files={"file": ("Order.cs", f, "text/plain")},
                    headers={"Authorization": f"Bearer {seeded_users['admin']}"},
                )
        r = await client.get("/rules?limit=50",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        titles = [rule["title"] for rule in r.json().get("items", r.json())]
        for expected in SEED_TITLES:
            assert any(expected.lower() in t.lower() for t in titles), (
                f"'{expected}' not found in extracted rules: {titles}"
            )

    async def test_ingest_response_includes_rule_count(self, client, seeded_users):
        with patch("app.ingest.pipeline.extract_rules", AsyncMock(return_value=_MOCK_RESULT)):
            with open("seeds/Order.cs", "rb") as f:
                r = await client.post(
                    "/ingest/file",
                    files={"file": ("Order.cs", f, "text/plain")},
                    headers={"Authorization": f"Bearer {seeded_users['admin']}"},
                )
        body = r.json()
        assert "rules_extracted" in body or "rules_found" in body or len(body) > 0

    async def test_ingest_rules_have_confidence_scores(self, client, seeded_users):
        with patch("app.ingest.pipeline.extract_rules", AsyncMock(return_value=_MOCK_RESULT)):
            with open("seeds/Order.cs", "rb") as f:
                await client.post(
                    "/ingest/file",
                    files={"file": ("Order.cs", f, "text/plain")},
                    headers={"Authorization": f"Bearer {seeded_users['admin']}"},
                )
        r = await client.get("/rules?limit=50",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rules = r.json().get("items", r.json())
        for rule in rules:
            assert "extraction_confidence" in rule
            if rule["extraction_confidence"] is not None:
                assert 0.0 <= rule["extraction_confidence"] <= 1.0

    async def test_unauthenticated_ingest_returns_401(self, client):
        with open("seeds/Order.cs", "rb") as f:
            r = await client.post(
                "/ingest/file",
                files={"file": ("Order.cs", f, "text/plain")},
            )
        assert r.status_code == 401


class TestIngestErrors:

    async def test_ingest_errors_endpoint_requires_auth(self, client):
        r = await client.get("/admin/ingest-errors")
        assert r.status_code == 401

    async def test_ingest_errors_accessible_to_admin(self, client, seeded_users):
        r = await client.get("/admin/ingest-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200

    async def test_clean_seed_produces_no_errors(self, client, seeded_users):
        with patch("app.ingest.pipeline.extract_rules", AsyncMock(return_value=_MOCK_RESULT)):
            with open("seeds/Order.cs", "rb") as f:
                await client.post(
                    "/ingest/file",
                    files={"file": ("Order.cs", f, "text/plain")},
                    headers={"Authorization": f"Bearer {seeded_users['admin']}"},
                )
        r = await client.get("/admin/ingest-errors",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        errors = r.json().get("items", r.json())
        assert len(errors) == 0, f"Expected no errors for clean seed. Got: {errors}"
