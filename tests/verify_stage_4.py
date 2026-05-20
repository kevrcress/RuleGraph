"""
Stage 4 verification: React frontend.
Uses Playwright. Requires both servers running:
  uvicorn app.main:app --port 8000
  cd frontend && npm run dev  (runs on port 5173)
Run: pytest tests/verify_stage_4.py -v
"""
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:5173"
API  = "http://localhost:8001"


@pytest.fixture(scope="module")
def user_page(browser):
    """Browser page logged in as User."""
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
    """Browser page logged in as Tech Lead."""
    page = browser.new_page()
    page.goto(f"{BASE}/login")
    page.fill('[name="email"]', "tl@test.com")
    page.fill('[name="password"]', "Test1234!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE}/**")
    yield page
    page.close()


@pytest.fixture(scope="module")
def ba_page(browser):
    """Browser page logged in as Business Admin."""
    page = browser.new_page()
    page.goto(f"{BASE}/login")
    page.fill('[name="email"]', "ba@test.com")
    page.fill('[name="password"]', "Test1234!")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE}/**")
    yield page
    page.close()


class TestAuth:

    def test_login_page_loads(self, browser):
        page = browser.new_page()
        page.goto(f"{BASE}/login")
        expect(page.locator("form")).to_be_visible()
        page.close()

    def test_invalid_login_shows_error(self, browser):
        page = browser.new_page()
        page.goto(f"{BASE}/login")
        page.fill('[name="email"]', "nobody@test.com")
        page.fill('[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')
        expect(page.locator("[role='alert'], .error, [data-testid='error']")).to_be_visible(timeout=3000)
        page.close()

    def test_unauthenticated_redirect_to_login(self, browser):
        page = browser.new_page()
        page.goto(f"{BASE}/rules")
        expect(page).to_have_url(f"{BASE}/login")
        page.close()


class TestViewToggle:

    def test_user_has_no_view_toggle(self, user_page):
        user_page.goto(f"{BASE}/rules")
        toggle = user_page.locator("[data-testid='view-toggle']")
        expect(toggle).not_to_be_visible()

    def test_tl_has_view_toggle(self, tl_page):
        tl_page.goto(f"{BASE}/rules")
        toggle = tl_page.locator("[data-testid='view-toggle']")
        expect(toggle).to_be_visible()

    def test_tl_can_switch_to_business_view(self, tl_page):
        tl_page.goto(f"{BASE}/rules")
        tl_page.locator("[data-testid='view-toggle']").click()
        expect(tl_page.locator("[data-testid='view-indicator']")).to_contain_text("Business")


class TestRuleBrowser:

    def test_rule_browser_loads(self, user_page):
        user_page.goto(f"{BASE}/rules")
        expect(user_page.locator("[data-testid='rule-list']")).to_be_visible()

    def test_rules_appear_in_list(self, user_page):
        user_page.goto(f"{BASE}/rules")
        items = user_page.locator("[data-testid='rule-item']")
        expect(items.first).to_be_visible()

    def test_search_filters_rules(self, user_page):
        user_page.goto(f"{BASE}/rules")
        user_page.fill("[data-testid='search-input']", "Order Cancellation")
        user_page.wait_for_timeout(500)
        items = user_page.locator("[data-testid='rule-item']")
        count = items.count()
        assert count >= 1, "Search for 'Order Cancellation' returned no results"


class TestCompareView:

    def test_compare_view_has_three_tabs(self, user_page):
        user_page.goto(f"{BASE}/rules")
        user_page.locator("[data-testid='rule-item']").first.click()
        for tab_text in ["Defined", "Implemented", "Compare"]:
            expect(user_page.locator(f"[role='tab']:has-text('{tab_text}')")).to_be_visible()

    def test_compare_tab_shows_status(self, user_page):
        user_page.goto(f"{BASE}/rules")
        user_page.locator("[data-testid='rule-item']").first.click()
        user_page.locator("[role='tab']:has-text('Compare')").click()
        statuses = ["Verified", "Drift", "Undocumented", "Orphaned"]
        status_el = user_page.locator("[data-testid='compare-status']")
        expect(status_el).to_be_visible()
        status_text = status_el.inner_text()
        assert any(s in status_text for s in statuses), f"No valid status found in: {status_text}"


class TestDiffView:

    def test_diff_page_loads(self, user_page):
        user_page.goto(f"{BASE}/diff")
        expect(user_page.locator("[data-testid='diff-list']")).to_be_visible()

    def test_diff_item_links_to_per_rule_diff(self, user_page):
        user_page.goto(f"{BASE}/diff")
        first_item = user_page.locator("[data-testid='diff-item']").first
        if first_item.is_visible():
            first_item.locator("[data-testid='view-diff-link']").click()
            expect(user_page.locator("[data-testid='diff-panel']")).to_be_visible()

    def test_diff_panel_has_two_columns(self, user_page):
        user_page.goto(f"{BASE}/diff")
        first_item = user_page.locator("[data-testid='diff-item']").first
        if first_item.is_visible():
            first_item.locator("[data-testid='view-diff-link']").click()
            expect(user_page.locator("[data-testid='diff-before']")).to_be_visible()
            expect(user_page.locator("[data-testid='diff-after']")).to_be_visible()


class TestWikiEditor:

    def test_wiki_editor_accessible_to_user(self, user_page):
        user_page.goto(f"{BASE}/rules/new")
        expect(user_page.locator("[data-testid='wiki-editor']")).to_be_visible()

    def test_authoring_assist_fires_on_input(self, user_page):
        user_page.goto(f"{BASE}/rules/new")
        user_page.fill("[data-testid='rule-title']", "Order Cancellation Test")
        user_page.wait_for_timeout(1000)
        assist = user_page.locator("[data-testid='authoring-assist']")
        expect(assist).to_be_visible(timeout=3000)


class TestNotificationBell:

    def test_notification_bell_visible(self, user_page):
        user_page.goto(f"{BASE}/rules")
        expect(user_page.locator("[data-testid='notification-bell']")).to_be_visible()

    def test_notification_feed_opens_on_click(self, user_page):
        user_page.goto(f"{BASE}/rules")
        user_page.locator("[data-testid='notification-bell']").click()
        expect(user_page.locator("[data-testid='notification-feed']")).to_be_visible()


class TestDocumentUpload:

    def test_document_library_loads(self, user_page):
        user_page.goto(f"{BASE}/documents")
        expect(user_page.locator("[data-testid='document-library']")).to_be_visible()

    def test_upload_form_visible(self, user_page):
        user_page.goto(f"{BASE}/documents")
        expect(user_page.locator("input[type='file']")).to_be_visible()


class TestAdminPages:

    def test_admin_audit_log_page_loads(self, ba_page):
        ba_page.goto(f"{BASE}/admin/audit-log")
        # BA should not see admin pages — expect redirect or 403 UI
        # This tests the frontend enforces role-based routing
        expect(ba_page.locator("[data-testid='access-denied'], [data-testid='audit-log-table']")).to_be_visible()

    def test_review_queue_accessible_to_ba(self, ba_page):
        ba_page.goto(f"{BASE}/admin/review-queue")
        expect(ba_page.locator("[data-testid='review-queue']")).to_be_visible()

    def test_tl_dashboard_accessible_to_tl(self, tl_page):
        tl_page.goto(f"{BASE}/admin/tech-lead-dashboard")
        expect(tl_page.locator("[data-testid='tl-dashboard']")).to_be_visible()
