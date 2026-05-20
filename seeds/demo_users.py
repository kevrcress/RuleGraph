"""
Demo user seeder — creates one user per role with known credentials.
Run: python seeds/demo_users.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.auth_service import register_user

DEMO_USERS = [
    {"username": "admin",          "email": "admin@test.com",  "name": "Admin User",    "password": "Test1234!", "role": "admin"},
    {"username": "business_admin", "email": "ba@test.com",     "name": "BA User",       "password": "Test1234!", "role": "business_admin"},
    {"username": "tech_lead",      "email": "tl@test.com",     "name": "TL User",       "password": "Test1234!", "role": "tech_lead"},
    {"username": "user",           "email": "user@test.com",   "name": "Regular User",  "password": "Test1234!", "role": "user"},
]


async def seed():
    engine = create_async_engine(settings.database_url)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        for u in DEMO_USERS:
            try:
                user = await register_user(db, u["username"], u["email"], u["name"], u["password"], role=u["role"])
                print(f"  Created {u['role']}: {u['email']}")
            except ValueError:
                print(f"  Already exists: {u['email']}")
    await engine.dispose()
    print("\nDemo users seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
