"""Integration tests for admin endpoints: audit log, user management, role guards."""
import pytest


class TestAuditLog:

    async def test_admin_can_read_audit_log(self, client, seeded_users):
        r = await client.get("/admin/audit-log",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200

    async def test_user_cannot_read_audit_log(self, client, seeded_users):
        r = await client.get("/admin/audit-log",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403

    async def test_ba_cannot_read_audit_log(self, client, seeded_users):
        r = await client.get("/admin/audit-log",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})
        assert r.status_code == 403

    async def test_audit_log_has_login_events(self, client, seeded_users):
        # seeded_users fixture logs in all users — audit events should be present
        r = await client.get("/admin/audit-log?limit=100",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        events = r.json().get("items", r.json())
        actions = [e.get("action", "") for e in events]
        assert "auth.login" in actions


class TestUserManagement:

    async def test_admin_can_list_users(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200
        users = r.json().get("items", r.json())
        assert len(users) > 0

    async def test_user_cannot_list_users(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403

    async def test_ba_cannot_list_users(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})
        assert r.status_code == 403


class TestTechLeadDashboard:

    async def test_tl_can_access_dashboard(self, client, seeded_users):
        r = await client.get("/admin/tech-lead-dashboard",
            headers={"Authorization": f"Bearer {seeded_users['tech_lead']}"})
        assert r.status_code == 200

    async def test_admin_can_access_dashboard(self, client, seeded_users):
        r = await client.get("/admin/tech-lead-dashboard",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200

    async def test_user_cannot_access_dashboard(self, client, seeded_users):
        r = await client.get("/admin/tech-lead-dashboard",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403


class TestWebhooks:

    async def test_webhook_no_signature_returns_401(self, client):
        r = await client.post("/webhooks/ado",
            content=b'{"eventType":"git.push"}',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401

    async def test_webhook_bad_signature_returns_401(self, client):
        r = await client.post("/webhooks/ado",
            content=b'{"eventType":"git.push"}',
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=deadbeef",
            },
        )
        assert r.status_code == 401

    async def test_webhook_valid_signature_returns_200(self, client):
        import hmac, hashlib, json
        from app.config import settings
        secret = getattr(settings, "webhook_test_secret", "test-webhook-secret")
        body = json.dumps({"eventType": "git.push", "resource": {}}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        r = await client.post("/webhooks/ado",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        assert r.status_code == 200
