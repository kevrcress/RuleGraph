"""
Shared fixtures for all stage verification tests.
"""
import asyncio
import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings

# Use a dedicated test database, never the dev database
TEST_DATABASE_URL = settings.database_url.replace(
    "/rulegraph", "/rulegraph_test"
)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def db_session(test_engine):
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

@pytest_asyncio.fixture(scope="session")
async def client(test_engine):
    """ASGI test client — no running server needed."""
    async def override_get_db():
        factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="session")
async def seeded_users(client):
    """Create one user per role. Returns dict of role -> token."""
    users = {
        "admin":          {"email": "admin@test.com",   "password": "Test1234!", "name": "Admin User",    "role": "admin"},
        "business_admin": {"email": "ba@test.com",      "password": "Test1234!", "name": "BA User",       "role": "business_admin"},
        "tech_lead":      {"email": "tl@test.com",      "password": "Test1234!", "name": "TL User",       "role": "tech_lead"},
        "user":           {"email": "user@test.com",    "password": "Test1234!", "name": "Regular User",  "role": "user"},
    }
    tokens = {}
    for role, u in users.items():
        r = await client.post("/auth/register", json={
            "username": role, "email": u["email"],
            "name": u["name"], "password": u["password"]
        })
        # If already exists from a previous run, just login
        r = await client.post("/auth/login", json={
            "email": u["email"], "password": u["password"]
        })
        assert r.status_code == 200, f"Login failed for {role}: {r.text}"
        tokens[role] = r.json()["access_token"]
    return tokens

def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
