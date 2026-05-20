"""Unit tests for JWT creation and validation (app/security/jwt.py)."""
import time
import pytest
from jose import jwt as _jose_jwt

from app.security.jwt import create_access_token, decode_access_token, ALGORITHM
from app.config import settings


USER_ID = "00000000-0000-0000-0000-000000000001"


def test_create_token_returns_string():
    token = create_access_token(USER_ID, "user", "u@test.com")
    assert isinstance(token, str)
    assert len(token.split(".")) == 3  # header.payload.signature


def test_decode_round_trip():
    token = create_access_token(USER_ID, "tech_lead", "tl@test.com",
                                name="TL User", username="tl")
    payload = decode_access_token(token)
    assert payload["sub"] == USER_ID
    assert payload["role"] == "tech_lead"
    assert payload["email"] == "tl@test.com"
    assert payload["name"] == "TL User"
    assert payload["username"] == "tl"


def test_token_has_exp_claim():
    token = create_access_token(USER_ID, "user", "u@test.com")
    payload = _jose_jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    assert "exp" in payload
    assert payload["exp"] > time.time()


def test_custom_ttl_reflected_in_expiry():
    now = time.time()
    token = create_access_token(USER_ID, "user", "u@test.com", ttl_minutes=5)
    payload = _jose_jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    # Should expire within ~5-6 minutes from now
    assert payload["exp"] <= now + 370  # 5min + 10s buffer
    assert payload["exp"] >= now + 280  # at least 4min50s


def test_expired_token_raises():
    token = create_access_token(USER_ID, "user", "u@test.com", ttl_minutes=-1)
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(token)


def test_tampered_token_raises():
    token = create_access_token(USER_ID, "user", "u@test.com")
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + ".badsignature"
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(tampered)


def test_wrong_secret_raises():
    token = _jose_jwt.encode(
        {"sub": USER_ID, "role": "user", "exp": int(time.time()) + 3600},
        "wrong-secret",
        algorithm=ALGORITHM,
    )
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(token)
