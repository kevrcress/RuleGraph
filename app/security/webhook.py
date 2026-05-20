"""HMAC-SHA256 webhook signature validation per Section 27."""
import hashlib
import hmac


def validate_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Return True if the HMAC-SHA256 of body matches signature."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
