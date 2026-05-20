"""Auth router — register and login with per-IP rate limits."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.security.rate_limit import check_rate_limit
from app.services.auth_service import login_user, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = _client_ip(request)
    allowed, _ = await check_rate_limit(f"register:{ip}", limit=5, window_seconds=3600)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many registration attempts. Try again later.")

    try:
        user = await register_user(
            db, body.username, body.email, body.name, body.password,
            role=body.role, ip_address=ip,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {"id": str(user.id), "username": user.username, "email": user.email, "role": user.role}


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = _client_ip(request)
    allowed, _ = await check_rate_limit(f"login:{ip}", limit=10, window_seconds=900)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    try:
        token = await login_user(db, body.email, body.password, ip_address=ip)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=token)
