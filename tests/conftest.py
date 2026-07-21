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


# ---------------------------------------------------------------------------
# Clear Redis rate-limit keys before any Stage 4 (Playwright) tests.
# Re-running the test suite would otherwise exhaust the per-IP login limit.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _clear_rate_limits(request):
    try:
        import redis as _redis_sync
        r = _redis_sync.from_url("redis://localhost:6379", decode_responses=True)
        for key in r.keys("rl:*"):
            r.delete(key)
        r.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Playwright browser fixture — patches page.goto() so that navigating away
# from /login waits for the rg_token to land in localStorage first.
# This is needed because Playwright's wait_for_url("/**") resolves
# immediately when the current URL (/login) already matches the glob pattern,
# which means the fixture yields before the async login fetch completes.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def browser(playwright, browser_type, browser_type_launch_args):
    _browser = browser_type.launch(**browser_type_launch_args)

    original_new_page = _browser.new_page

    def _patched_new_page(*args, **kwargs):
        page = original_new_page(*args, **kwargs)
        _original_goto = page.goto

        def _patched_goto(url, *goto_args, **goto_kwargs):
            try:
                if "/login" in page.url:
                    token = page.evaluate('localStorage.getItem("rg_token")')
                    if token is None:
                        page.wait_for_function(
                            'localStorage.getItem("rg_token") !== null',
                            timeout=5000,
                        )
            except Exception:
                pass
            return _original_goto(url, *goto_args, **goto_kwargs)

        page.goto = _patched_goto
        return page

    _browser.new_page = _patched_new_page

    yield _browser
    _browser.close()

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
    # ASGITransport does NOT run FastAPI startup events, so app.state.arq_pool is
    # never created here. Provide a mock pool so ingest routes can enqueue jobs
    # without a live Redis worker. Tests that assert on enqueue patch this mock.
    from unittest.mock import AsyncMock
    app.state.arq_pool = AsyncMock()
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
            "name": u["name"], "password": u["password"],
            "role": u["role"],
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

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _auto_seed_stage2(request, client):
    """
    Seed eShop multi-source data when verify_stage_2.py tests are collected.
    Runs once per test session, before any Stage 2 tests execute.
    No-op when running Stage 1 tests only.
    """
    stage2_collected = any(
        "verify_stage_2" in item.nodeid
        for item in request.session.items
    )
    if not stage2_collected:
        return

    try:
        from seeds.eshop_seed import seed_test_data
        await seed_test_data(client)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Stage 2 seed failed (tests may fail): {e}"
        )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _auto_seed_stage5(request, client, seeded_users):
    """
    Seed Order.cs when verify_stage_5.py tests are collected so that
    chat sources are available. No-op in other test sessions.
    """
    stage5_collected = any(
        "verify_stage_5" in item.nodeid
        for item in request.session.items
    )
    # If Stage 1 or 2 tests are also collected they seed the same data; skip duplicate.
    stage1_or_2_collected = any(
        ("verify_stage_1" in item.nodeid or "verify_stage_2" in item.nodeid)
        for item in request.session.items
    )
    if not stage5_collected or stage1_or_2_collected:
        return

    try:
        import logging
        log = logging.getLogger(__name__)
        admin_token = seeded_users["admin"]
        with open("seeds/Order.cs", "rb") as f:
            r = await client.post(
                "/ingest/file",
                files={"file": ("Order.cs", f, "text/plain")},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        if r.status_code == 200:
            log.info("Stage 5 seed: Order.cs ingested for chat source tests")
        else:
            log.warning("Stage 5 seed: Order.cs ingest returned %s — %s", r.status_code, r.text)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Stage 5 seed failed (chat source tests may fail): {e}"
        )
