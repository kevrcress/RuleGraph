"""Auth request/response schemas."""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    username: str
    email: str
    name: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
