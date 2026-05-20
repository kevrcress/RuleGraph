"""Auth service — register, login, audit log helpers."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User
from app.security.jwt import create_access_token, DEFAULT_TTL_MINUTES

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def write_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.warning("Failed to write audit log: %s", exc)


async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    name: str,
    password: str,
    role: str = "user",
    ip_address: Optional[str] = None,
) -> User:
    existing = await db.execute(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing.scalar_one_or_none():
        raise ValueError("User with that email or username already exists")

    user = User(
        username=username,
        email=email,
        name=name,
        password_hash=pwd_context.hash(password),
        role=role,
    )
    db.add(user)
    await db.flush()  # get the id
    await write_audit(db, "user.created", user_id=user.id, target_type="user", target_id=user.id, ip_address=ip_address)
    return user


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ip_address: Optional[str] = None,
) -> str:
    result = await db.execute(select(User).where(User.email == email))
    user: Optional[User] = result.scalar_one_or_none()

    if user is None or not pwd_context.verify(password, user.password_hash):
        if user:
            await write_audit(db, "auth.login_failed", user_id=user.id, ip_address=ip_address, detail={"email": email})
        else:
            await write_audit(db, "auth.login_failed", ip_address=ip_address, detail={"email": email})
        raise ValueError("Invalid email or password")

    # Update last_active
    user.last_active = datetime.now(timezone.utc)
    await db.flush()
    await write_audit(db, "auth.login", user_id=user.id, target_type="user", target_id=user.id, ip_address=ip_address)

    return create_access_token(str(user.id), user.role, user.email, ttl_minutes)
