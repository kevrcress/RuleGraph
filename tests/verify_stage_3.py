"""
Stage 3 verification: Auth, roles, approval chain, audit log,
webhook HMAC, rate limiting basics.
"""
import hmac
import hashlib
import json
import pytest
import pytest_asyncio


class TestAuthEndpoints:

    async def test_register_returns_201(self, client):
        r = await client.post("/auth/register", json={
            "username": "newuser_s3", "email": "newuser_s3@test.com",
            "name": "New User", "password": "Test1234!"
        })
        assert r.status_code in (200, 201), f"Register failed: {r.text}"

    async def test_login_returns_token(self, client):
        r = await client.post("/auth/login", json={
            "email": "user@test.com", "password": "Test1234!"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_wrong_password_returns_401(self, client):
        r = await client.post("/auth/login", json={
            "email": "user@test.com", "password": "wrongpassword"
        })
        assert r.status_code == 401

    async def test_unauthenticated_request_returns_401(self, client):
        r = await client.get("/rules")
        assert r.status_code == 401


class TestRoleEnforcement:

    async def test_user_cannot_access_admin_endpoints(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403

    async def test_ba_cannot_access_admin_user_management(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})
        assert r.status_code == 403

    async def test_admin_can_access_user_management(self, client, seeded_users):
        r = await client.get("/admin/users",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200

    async def test_user_can_access_rules(self, client, seeded_users):
        r = await client.get("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 200

    async def test_tl_can_access_tl_dashboard(self, client, seeded_users):
        r = await client.get("/admin/tech-lead-dashboard",
            headers={"Authorization": f"Bearer {seeded_users['tech_lead']}"})
        assert r.status_code == 200

    async def test_user_cannot_access_tl_dashboard(self, client, seeded_users):
        r = await client.get("/admin/tech-lead-dashboard",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403


class TestApprovalChain:

    @pytest_asyncio.fixture
    async def proposed_rule(self, client, seeded_users):
        """Propose a rule as User and return its ID."""
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Test Approval Rule", "definition": "A rule for testing the approval chain."}
        )
        assert r.status_code in (200, 201), f"Propose failed: {r.text}"
        return r.json()["id"]

    async def test_proposed_rule_has_proposed_status(self, client, seeded_users, proposed_rule):
        r = await client.get(f"/rules/{proposed_rule}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.json()["status"] == "proposed"

    async def test_ba_can_approve_rule(self, client, seeded_users, proposed_rule):
        r = await client.put(f"/admin/review-queue/{proposed_rule}/approve",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})
        assert r.status_code == 200
        rule = (await client.get(f"/rules/{proposed_rule}",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})).json()
        assert rule["status"] == "approved"

    async def test_ba_can_reject_rule_with_notes(self, client, seeded_users):
        # Propose a fresh rule
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Rule To Reject", "definition": "This one will be rejected."}
        )
        rule_id = r.json()["id"]
        # Reject with note
        r2 = await client.put(f"/admin/review-queue/{rule_id}/reject",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"},
            json={"rejection_note": "Please clarify the scope of this rule."}
        )
        assert r2.status_code == 200
        rule = (await client.get(f"/rules/{rule_id}",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})).json()
        assert rule["status"] == "proposed", "Rejected rule should return to proposed"
        # Check rejection note is stored in lineage
        lineage = (await client.get(f"/rules/{rule_id}/lineage",
            headers={"Authorization": f"Bearer {seeded_users['business_admin']}"})).json()
        notes = [e.get("rejection_note") for e in lineage.get("events", lineage) if e.get("rejection_note")]
        assert len(notes) > 0, "Rejection note not found in lineage"

    async def test_user_cannot_approve_rules(self, client, seeded_users):
        r = await client.post("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"title": "Rule For Perm Test", "definition": "Testing permissions."}
        )
        rule_id = r.json()["id"]
        r2 = await client.put(f"/admin/review-queue/{rule_id}/approve",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r2.status_code == 403

    async def test_lineage_recorded_for_rule_changes(self, client, seeded_users, proposed_rule):
        r = await client.get(f"/rules/{proposed_rule}/lineage",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 200
        events = r.json().get("events", r.json())
        assert len(events) > 0, "Expected at least one lineage event"


class TestAuditLog:

    async def test_audit_log_accessible_to_admin(self, client, seeded_users):
        r = await client.get("/admin/audit-log",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        assert r.status_code == 200

    async def test_audit_log_not_accessible_to_user(self, client, seeded_users):
        r = await client.get("/admin/audit-log",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 403

    async def test_audit_log_contains_login_events(self, client, seeded_users):
        r = await client.get("/admin/audit-log?limit=100",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        events = r.json().get("items", r.json())
        actions = [e["action"] for e in events]
        assert "auth.login" in actions, "Expected auth.login events in audit log"

    async def test_audit_log_contains_rule_events(self, client, seeded_users):
        r = await client.get("/admin/audit-log?limit=100",
            headers={"Authorization": f"Bearer {seeded_users['admin']}"})
        events = r.json().get("items", r.json())
        actions = [e["action"] for e in events]
        assert "rule.proposed" in actions, "Expected rule.proposed events in audit log"


class TestWebhookSecurity:

    async def test_webhook_without_signature_returns_401(self, client):
        r = await client.post("/webhooks/ado",
            content=b'{"eventType":"git.push"}',
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code == 401

    async def test_webhook_with_wrong_signature_returns_401(self, client):
        body = b'{"eventType":"git.push"}'
        r = await client.post("/webhooks/ado",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalidsignature"
            }
        )
        assert r.status_code == 401

    async def test_webhook_with_valid_signature_returns_200(self, client, seeded_users):
        # Get the webhook secret from settings (in test mode, use a known test secret)
        from app.config import settings
        secret = getattr(settings, "webhook_test_secret", "test-webhook-secret")
        body = json.dumps({"eventType": "git.push", "resource": {}}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        r = await client.post("/webhooks/ado",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig
            }
        )
        # Webhook should accept (200) and queue async job
        assert r.status_code == 200
