"""JWT token creation and validation. TTL from system settings, signed with JWT_SECRET_KEY."""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
DEFAULT_TTL_MINUTES = 60


def create_access_token(
    user_id: str,
    role: str,
    email: str,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc
