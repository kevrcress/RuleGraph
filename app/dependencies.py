"""FastAPI dependency helpers — DB session, JWT auth, role guards."""
from typing import Callable, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.jwt import decode_access_token

__all__ = ["get_db", "get_current_user", "require_roles"]

# auto_error=False so we can return 401 (not 403) when the header is absent
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Validate the Bearer JWT. Raises 401 when absent or invalid."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_roles(*roles: str) -> Callable:
    """Return a dependency that checks the JWT role against the allowed set."""
    async def _guard(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _guard
