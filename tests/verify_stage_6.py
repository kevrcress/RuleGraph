"""
Stage 6 verification: Impact analysis, feedback signals, scoring loop,
QA wiki, wiki promotion.
"""
import pytest
import pytest_asyncio


class TestImpactAnalysis:

    @pytest_asyncio.fixture
    async def stock_rule_id(self, client, seeded_users):
        """Find the Stock Confirmation rule seeded in Stage 1."""
        r = await client.get("/rules?limit=50",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rules = r.json().get("items", r.json())
        match = next(
            (r for r in rules if "stock" in r["title"].lower()), None
        )
        if not match:
            pytest.skip("Stock Confirmation rule not found — check Stage 1 seed")
        return match["id"]

    async def test_impact_endpoint_returns_200(self, client, seeded_users, stock_rule_id):
        r = await client.get(f"/rules/{stock_rule_id}/impact",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r.status_code == 200

    async def test_impact_lists_affected_services(self, client, seeded_users, stock_rule_id):
        r = await client.get(f"/rules/{stock_rule_id}/impact",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        body = r.json()
        services = body.get("services", [])
        assert len(services) >= 1, "Expected at least one affected service in impact analysis"

    async def test_impact_lists_affected_tests(self, client, seeded_users, stock_rule_id):
        r = await client.get(f"/rules/{stock_rule_id}/impact",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        body = r.json()
        # tests key may be empty if no tests found, but key must exist
        assert "tests" in body, "Impact response missing 'tests' key"

    async def test_reverse_impact_returns_200(self, client, seeded_users, stock_rule_id):
        r = await client.get(f"/rules/{stock_rule_id}/impact/reverse",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r.status_code == 200

    async def test_impact_business_view_hides_file_paths(self, client, seeded_users, stock_rule_id):
        r = await client.get(f"/rules/{stock_rule_id}/impact?view=business",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        body = r.json()
        body_str = str(body)
        assert ".cs" not in body_str and "/" not in body_str.replace("http", ""), (
            "Business view should not contain file paths"
        )


class TestFeedbackAndScoringLoop:

    @pytest_asyncio.fixture
    async def rule_id(self, client, seeded_users):
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        return r.json().get("items", r.json())[0]["id"]

    async def test_feedback_endpoint_accepts_thumbs_up(self, client, seeded_users, rule_id):
        r = await client.post("/feedback",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"signal_type": "thumbs_up", "rule_id": rule_id}
        )
        assert r.status_code in (200, 201)

    async def test_feedback_endpoint_accepts_thumbs_down(self, client, seeded_users, rule_id):
        r = await client.post("/feedback",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"signal_type": "thumbs_down", "rule_id": rule_id}
        )
        assert r.status_code in (200, 201)

    async def test_feedback_endpoint_accepts_mark_verified(self, client, seeded_users, rule_id):
        r = await client.post("/feedback",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"signal_type": "mark_as_verified", "rule_id": rule_id}
        )
        assert r.status_code in (200, 201)

    async def test_improve_updates_graph_quality_score(self, client, seeded_users, rule_id):
        # Record a strong positive signal
        await client.post("/feedback",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"signal_type": "mark_as_verified", "rule_id": rule_id}
        )
        # Get score before improve
        before = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json()
        score_before = before.get("graph_quality_score")

        # Run improve
        r = await client.post("/improve",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"}
        )
        assert r.status_code == 200

        # Score should have changed (or been set if it was None)
        after = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json()
        score_after = after.get("graph_quality_score")
        assert score_after is not None, "graph_quality_score should be set after /improve"
        if score_before is not None:
            assert score_after != score_before, "Score should change after feedback + improve"

    async def test_negative_signal_lowers_score(self, client, seeded_users, rule_id):
        # Record strong negative
        await client.post("/feedback",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"signal_type": "this_is_wrong", "rule_id": rule_id}
        )
        score_before = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json().get("graph_quality_score", 1.0)

        await client.post("/improve",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"}
        )
        score_after = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})).json().get("graph_quality_score", 1.0)

        assert score_after <= score_before, (
            f"Negative signal should not increase score. Before: {score_before}, After: {score_after}"
        )


class TestQAWikiAndPromotion:

    async def test_wiki_promote_endpoint_exists(self, client, seeded_users):
        r = await client.post("/wiki/promote",
            headers={"Authorization": f"Bearer {seeded_users['tech_lead']}"},
            json={"change_ids": []}
        )
        # Empty list is a no-op but endpoint should respond
        assert r.status_code in (200, 204, 400), f"Unexpected status: {r.status_code}"

    async def test_wiki_promote_requires_tl_or_admin(self, client, seeded_users):
        r = await client.post("/wiki/promote",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"change_ids": []}
        )
        assert r.status_code == 403
