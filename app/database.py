"""
Async SQLAlchemy engine and session factory.
Exports Base (for models) and get_db (for dependency injection).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            # Auto-kill any session idle in transaction for >30s.
            # Prevents a stuck background task from blocking DDL migrations.
            "idle_in_transaction_session_timeout": "30000",
        }
    },
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Usable outside of request context (e.g. background tasks)
async_session_factory = AsyncSessionLocal
