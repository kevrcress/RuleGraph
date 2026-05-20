"""Integration tests for rules CRUD and role enforcement."""
import pytest


class TestRulesRead:

    async def test_rules_list_is_paginated(self, client, seeded_users):
        r = await client.get("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        body = r.json()
        assert "items" in body or isinstance(body, list)

    async def test_rules_limit_param_respected(self, client, seeded_users):
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        items = r.json().get("items", r.json())
        assert len(items) <= 1

    async def test_rule_detail_has_required_fields(self, client, seeded_users):
        # First ensure at least one rule exists
        await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Field Check Rule", "definition": "Checking fields."},
        )
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rule_id = r.json().get("items", r.json())[0]["id"]
        detail = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json()
        for field in ["id", "title", "status"]:
            assert field in detail, f"Rule missing field: {field}"

    async def test_unknown_rule_id_returns_404(self, client, seeded_users):
        r = await client.get("/rules/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 404


class TestRulesCreate:

    async def test_user_can_propose_rule(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "New Integration Rule", "definition": "For testing."},
        )
        assert r.status_code in (200, 201)
        body = r.json()
        assert body["status"] == "proposed"
        assert "id" in body

    async def test_proposed_rule_visible_in_list(self, client, seeded_users):
        title = "Visibility Test Rule"
        await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": title, "definition": "Should appear in list."},
        )
        r = await client.get("/rules?limit=50",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        titles = [item["title"] for item in r.json().get("items", r.json())]
        assert any(title in t for t in titles)

    async def test_rule_without_title_returns_422(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"definition": "Missing title."},
        )
        assert r.status_code == 422


class TestApprovalWorkflow:

    async def test_ba_can_approve_proposed_rule(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Rule For Approval", "definition": "Approve me."},
        )
        rule_id = r.json()["id"]
        approve = await client.put(
            f"/admin/review-queue/{rule_id}/approve",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"},
        )
        assert approve.status_code == 200
        detail = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json()
        assert detail["status"] == "approved"

    async def test_regular_user_cannot_approve(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Permission Test Rule", "definition": "Test."},
        )
        rule_id = r.json()["id"]
        r2 = await client.put(
            f"/admin/review-queue/{rule_id}/approve",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
        )
        assert r2.status_code == 403


class TestLineage:

    async def test_lineage_recorded_after_proposal(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Lineage Test Rule", "definition": "Track my lineage."},
        )
        rule_id = r.json()["id"]
        lineage = (await client.get(f"/rules/{rule_id}/lineage",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json()
        events = lineage.get("events", lineage)
        assert len(events) > 0
