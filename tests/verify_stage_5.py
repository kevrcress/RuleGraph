"""
Stage 5 verification: Chat interface, subscriptions, in-app notifications.
"""
import pytest
import pytest_asyncio


class TestChatInterface:

    async def test_chat_returns_200(self, client, seeded_users):
        r = await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "How does order cancellation work?",
                  "session_id": "test-session-s5", "view": "business"}
        )
        assert r.status_code == 200

    async def test_chat_response_has_required_fields(self, client, seeded_users):
        r = await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "What business rules exist?",
                  "session_id": "test-session-s5b", "view": "business"}
        )
        body = r.json()
        assert "message" in body or "response" in body, f"Chat response missing message: {body}"
        assert "confidence" in body or "sources" in body, f"Chat response missing confidence/sources: {body}"

    async def test_chat_response_cites_sources(self, client, seeded_users):
        r = await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "Tell me about order cancellation",
                  "session_id": "test-session-s5c", "view": "business"}
        )
        body = r.json()
        sources = body.get("sources", [])
        assert len(sources) > 0, "Expected at least one source cited in chat response"

    async def test_chat_session_memory(self, client, seeded_users):
        session = "memory-test-session"
        await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "How does order cancellation work?",
                  "session_id": session, "view": "business"}
        )
        r2 = await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "What services does that involve?",
                  "session_id": session, "view": "business"}
        )
        assert r2.status_code == 200
        # Response should reference context from previous message without re-explaining
        body = r2.json()
        response_text = body.get("message", body.get("response", ""))
        assert len(response_text) > 20, "Follow-up response seems empty"

    async def test_chat_history_endpoint(self, client, seeded_users):
        session = "history-test-session"
        await client.post("/chat",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"message": "Hello", "session_id": session, "view": "business"}
        )
        r = await client.get(f"/chat/history?session_id={session}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r.status_code == 200
        history = r.json().get("messages", r.json())
        assert len(history) >= 1


class TestSubscriptions:

    @pytest_asyncio.fixture
    async def rule_id(self, client, seeded_users):
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        return r.json().get("items", r.json())[0]["id"]

    async def test_subscribe_to_rule(self, client, seeded_users, rule_id):
        r = await client.post("/subscriptions",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"target_type": "rule", "target_id": rule_id}
        )
        assert r.status_code in (200, 201)

    async def test_subscriptions_list(self, client, seeded_users, rule_id):
        await client.post("/subscriptions",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"target_type": "rule", "target_id": rule_id}
        )
        r = await client.get("/subscriptions",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r.status_code == 200
        subs = r.json().get("items", r.json())
        assert any(s["target_id"] == rule_id for s in subs), "Subscription not found"

    async def test_unsubscribe(self, client, seeded_users, rule_id):
        r = await client.post("/subscriptions",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"target_type": "rule", "target_id": rule_id}
        )
        sub_id = r.json()["id"]
        r2 = await client.delete(f"/subscriptions/{sub_id}",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r2.status_code in (200, 204)


class TestNotifications:

    @pytest_asyncio.fixture
    async def subscribed_rule(self, client, seeded_users):
        r = await client.get("/rules?limit=1",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        rule_id = r.json().get("items", r.json())[0]["id"]
        await client.post("/subscriptions",
            headers={"Authorization": f"Bearer {seeded_users['user']}"},
            json={"target_type": "rule", "target_id": rule_id}
        )
        return rule_id

    async def test_notifications_endpoint_returns_200(self, client, seeded_users):
        r = await client.get("/notifications",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r.status_code == 200

    async def test_notification_created_on_rule_drift(self, client, seeded_users, subscribed_rule):
        # Simulate drift by updating rule status
        await client.put(f"/rules/{subscribed_rule}",
            headers={"Authorization": f"Bearer {seeded_users['tech_lead']}"},
            json={"status": "drift"}
        )
        r = await client.get("/notifications",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        notifications = r.json().get("items", r.json())
        drift_notes = [n for n in notifications if "drift" in n.get("type", "").lower()
                       or "drift" in n.get("message", "").lower()]
        assert len(drift_notes) > 0, "Expected a drift notification for subscribed rule"

    async def test_mark_notification_read(self, client, seeded_users):
        r = await client.get("/notifications",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        notifications = r.json().get("items", r.json())
        if not notifications:
            pytest.skip("No notifications to mark read")
        note_id = notifications[0]["id"]
        r2 = await client.put(f"/notifications/{note_id}/read",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        assert r2.status_code == 200
        r3 = await client.get("/notifications",
            headers={"Authorization": f"Bearer {seeded_users['user']}"}
        )
        updated = next(n for n in r3.json().get("items", r3.json()) if n["id"] == note_id)
        assert updated["read"] is True
