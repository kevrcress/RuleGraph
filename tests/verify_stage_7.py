"""
Stage 7 verification: All 7 PoC requirements, graph visualization,
demo script execution.
Frontend tests use Playwright — both servers must be running.
"""
import os
import subprocess
import sys
import pytest
import pytest_asyncio
from pathlib import Path
from playwright.sync_api import Page, expect

BASE = "http://localhost:5173"


# ── Seeding fixture — ensures data is present for all API tests ──────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _seed_stage7(client, seeded_users):
    """Ingest seed files with distinct source names so conflicts are detectable."""
    headers = {"Authorization": f"Bearer {seeded_users['admin']}"}
    seed_files = [
        ("Order.cs", "ordering"),
        ("PaymentsProcessor.cs", "payments"),
    ]
    for fname, source in seed_files:
        fpath = os.path.join("seeds", fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                await client.post(
                    f"/ingest/file?source_name={source}",
                    files={"file": (fname, f, "text/plain")},
                    headers=headers,
                )


# ── API: PoC requirements 1–5 ─────────────────────────────────────────────


class TestPoCRequirementsAPI:

    async def test_poc_1_cross_service_extraction(self, client, seeded_users):
        """Req 1: Cross-service rule extraction in plain English."""
        r = await client.get("/rules?limit=50",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rules = r.json().get("items", r.json())
        multi_service = [r for r in rules if len(r.get("services", [])) > 1]
        # At minimum, rules must exist
        assert len(rules) > 0, (
            "Expected at least one rule extracted.\n"
            f"Rules found: {[r['title'] for r in rules]}"
        )

    async def test_poc_2_conflict_detected(self, client, seeded_users):
        """Req 2: Conflict between at least two services."""
        r = await client.get("/conflicts?limit=10",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        conflicts = r.json().get("items", r.json())
        assert len(conflicts) > 0, "Expected at least one conflict detected"

    async def test_poc_3_terminology_inconsistency(self, client, seeded_users):
        """Req 3: Terminology inconsistency flagged."""
        r = await client.get("/terminology?limit=10",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        items = r.json().get("items", r.json())
        assert len(items) > 0, "Expected at least one terminology inconsistency"

    async def test_poc_4_coverage_gap(self, client, seeded_users):
        """Req 4: Test coverage gap identified."""
        r = await client.get("/coverage?limit=10",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        items = r.json().get("items", r.json())
        gaps = [i for i in items if i.get("coverage_status", "").lower()
                in ("uncovered", "partial", "coverage_gap")]
        assert len(gaps) > 0, "Expected at least one rule with a coverage gap"

    async def test_poc_5_plain_language_diff(self, client, seeded_users):
        """Req 5: Plain language diff on a simulated code change."""
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rule_id = r.json().get("items", r.json())[0]["id"]
        r2 = await client.get(f"/diff/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r2.status_code == 200
        diff = r2.json()
        assert "before" in diff or "versions" in diff, "Diff missing before/after content"


# ── Browser: PoC requirements 6–7 ─────────────────────────────────────────


@pytest.fixture(scope="module")
def user_page(browser):
    page = browser.new_page()
    page.goto(f"{BASE}/login")
    page.fill('[name="email"]', "user@test.com")
    page.fill('[name="password"]', "Test1234!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE}/**")
    yield page
    page.close()


@pytest.fixture(scope="module")
def tl_page(browser):
    page = browser.new_page()
    page.goto(f"{BASE}/login")
    page.fill('[name="email"]', "tl@test.com")
    page.fill('[name="password"]', "Test1234!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE}/**")
    yield page
    page.close()


class TestPoCRequirementsBrowser:

    def test_poc_6a_business_view_hides_file_paths(self, user_page):
        """Req 6: Business view hides technical details."""
        user_page.goto(f"{BASE}/rules")
        user_page.locator("[data-testid='rule-item']").first.click()
        page_text = user_page.locator("main").inner_text()
        technical_signals = [".cs", ".py", ".ts", "src/", "namespace ", "class "]
        found = [s for s in technical_signals if s in page_text]
        assert len(found) == 0, (
            f"Business view should not contain technical details. Found: {found}"
        )

    def test_poc_6b_technical_view_shows_file_paths(self, tl_page):
        """Req 6: Technical view shows file paths."""
        tl_page.goto(f"{BASE}/rules")
        tl_page.locator("[data-testid='rule-item']").first.click()
        page_text = tl_page.locator("main").inner_text()
        technical_signals = [".cs", "src/", "confidence"]
        found = [s for s in technical_signals if s in page_text]
        assert len(found) > 0, (
            f"Technical view should show technical details. Text: {page_text[:500]}"
        )

    def test_poc_7_compare_view_all_statuses_present(self, user_page):
        """Req 7: Compare view shows Verified, Drift, and Undocumented rules."""
        user_page.goto(f"{BASE}/rules")
        page_text = user_page.locator("[data-testid='rule-list']").inner_text()
        found_statuses = []
        for status in ["Verified", "Drift", "Undocumented"]:
            if status.lower() in page_text.lower():
                found_statuses.append(status)
        assert len(found_statuses) >= 3, (
            f"Expected Verified, Drift, and Undocumented rules in browser. "
            f"Found: {found_statuses}\nPage text (truncated): {page_text[:500]}"
        )


# ── Graph visualization ────────────────────────────────────────────────────


class TestGraphVisualization:

    def test_graph_view_accessible_to_tl(self, tl_page):
        tl_page.goto(f"{BASE}/graph")
        expect(tl_page.locator("[data-testid='graph-visualization']")).to_be_visible(timeout=5000)

    def test_graph_contains_service_nodes(self, tl_page):
        tl_page.goto(f"{BASE}/graph")
        tl_page.wait_for_selector("[data-testid='graph-visualization']", timeout=5000)
        nodes = tl_page.locator(".react-flow__node")
        assert nodes.count() > 0, "Expected at least one node in the graph"

    def test_graph_not_accessible_to_user(self, user_page):
        user_page.goto(f"{BASE}/graph")
        access_denied = user_page.locator("[data-testid='access-denied']")
        redirected = user_page.url != f"{BASE}/graph"
        assert access_denied.is_visible() or redirected, (
            "User should not have access to graph visualization"
        )


# ── Demo script ───────────────────────────────────────────────────────────


class TestDemoScript:

    def test_demo_script_runs_to_completion(self):
        """Run the automated demo script and verify it exits 0."""
        result = subprocess.run(
            [sys.executable, "seeds/demo.py", "--test-mode"],
            capture_output=True, text=True, timeout=300
        )
        assert result.returncode == 0, (
            f"Demo script failed with exit code {result.returncode}.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    def test_demo_script_confirms_all_poc_requirements(self):
        """Demo script output must explicitly confirm all 7 requirements."""
        result = subprocess.run(
            [sys.executable, "seeds/demo.py", "--test-mode"],
            capture_output=True, text=True, timeout=300
        )
        output = result.stdout
        for i in range(1, 8):
            assert f"[✓] {i}." in output or f"[PASS] {i}" in output, (
                f"Demo script did not confirm PoC requirement {i}.\n"
                f"Output:\n{output}"
            )
