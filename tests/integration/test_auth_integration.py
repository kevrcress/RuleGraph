"""Integration tests for auth endpoints (register, login, token validation)."""
import pytest


class TestRegister:

    async def test_register_new_user_returns_201(self, client):
        r = await client.post("/auth/register", json={
            "username": "integ_user1",
            "email": "integ_user1@test.com",
            "name": "Integration User",
            "password": "Test1234!",
        })
        assert r.status_code == 201

    async def test_register_returns_id_and_role(self, client):
        r = await client.post("/auth/register", json={
            "username": "integ_user2",
            "email": "integ_user2@test.com",
            "name": "Integration User 2",
            "password": "Test1234!",
        })
        body = r.json()
        assert "id" in body
        assert body["role"] == "user"

    async def test_duplicate_email_returns_409(self, client, seeded_users):
        r = await client.post("/auth/register", json={
            "username": "dupe",
            "email": "user@test.com",  # already seeded
            "name": "Dupe",
            "password": "Test1234!",
        })
        assert r.status_code == 409

    async def test_register_weak_password_still_accepted(self, client):
        # Auth service does not enforce password strength — just hashes it
        r = await client.post("/auth/register", json={
            "username": "integ_weakpw",
            "email": "weakpw@test.com",
            "name": "Weak PW",
            "password": "a",
        })
        assert r.status_code == 201


class TestLogin:

    async def test_login_returns_access_token(self, client, seeded_users):
        r = await client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "Test1234!",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert r.json()["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client):
        r = await client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "wrongpassword",
        })
        assert r.status_code == 401

    async def test_login_unknown_email_returns_401(self, client):
        r = await client.post("/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "Test1234!",
        })
        assert r.status_code == 401

    async def test_login_stores_correct_role_in_token(self, client, seeded_users):
        from app.security.jwt import decode_access_token
        r = await client.post("/auth/login", json={
            "email": "tl@test.com",
            "password": "Test1234!",
        })
        token = r.json()["access_token"]
        payload = decode_access_token(token)
        assert payload["role"] == "tech_lead"

    async def test_login_token_contains_name_and_username(self, client, seeded_users):
        from app.security.jwt import decode_access_token
        r = await client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "Test1234!",
        })
        payload = decode_access_token(r.json()["access_token"])
        assert "name" in payload
        assert "username" in payload


class TestProtectedEndpoints:

    async def test_unauthenticated_rules_returns_401(self, client):
        r = await client.get("/rules")
        assert r.status_code == 401

    async def test_authenticated_rules_returns_200(self, client, seeded_users):
        r = await client.get("/rules",
            headers={"Authorization": f"Bearer {seeded_users['user']}"})
        assert r.status_code == 200

    async def test_expired_token_returns_401(self, client):
        from app.security.jwt import create_access_token
        expired = create_access_token("fake-id", "user", "x@x.com", ttl_minutes=-1)
        r = await client.get("/rules",
            headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401

    async def test_malformed_token_returns_401(self, client):
        r = await client.get("/rules",
            headers={"Authorization": "Bearer notavalidtoken"})
        assert r.status_code == 401
