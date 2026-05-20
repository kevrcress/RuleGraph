"""Unit tests for password hashing and webhook HMAC validation."""
import hashlib
import hmac

from app.services.auth_service import _hash_pw, _verify_pw
from app.security.webhook import validate_webhook_signature


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def test_hash_is_not_plaintext():
    hashed = _hash_pw("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_correct_password():
    pw = "Test1234!"
    hashed = _hash_pw(pw)
    assert _verify_pw(pw, hashed) is True


def test_verify_wrong_password():
    hashed = _hash_pw("Test1234!")
    assert _verify_pw("wrongpassword", hashed) is False


def test_two_hashes_of_same_password_differ():
    # bcrypt generates a new salt each time
    h1 = _hash_pw("same")
    h2 = _hash_pw("same")
    assert h1 != h2


def test_verify_empty_password_fails():
    hashed = _hash_pw("secret")
    assert _verify_pw("", hashed) is False


def test_verify_handles_garbage_hash_gracefully():
    # Should return False, not raise
    assert _verify_pw("password", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# Webhook HMAC-SHA256 validation
# ---------------------------------------------------------------------------

def _make_sig(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    body = b'{"eventType":"git.push"}'
    secret = "test-secret"
    sig = _make_sig(body, secret)
    assert validate_webhook_signature(body, sig, secret) is True


def test_wrong_signature_rejected():
    body = b'{"eventType":"git.push"}'
    assert validate_webhook_signature(body, "deadbeef", "test-secret") is False


def test_tampered_body_rejected():
    secret = "test-secret"
    original = b'{"eventType":"git.push"}'
    sig = _make_sig(original, secret)
    tampered = b'{"eventType":"git.push","injected":true}'
    assert validate_webhook_signature(tampered, sig, secret) is False


def test_wrong_secret_rejected():
    body = b'{"eventType":"git.push"}'
    sig = _make_sig(body, "real-secret")
    assert validate_webhook_signature(body, sig, "wrong-secret") is False


def test_empty_body_valid_signature():
    body = b""
    secret = "s"
    sig = _make_sig(body, secret)
    assert validate_webhook_signature(body, sig, secret) is True
