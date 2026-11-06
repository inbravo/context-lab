"""auth.py — Token-based authentication for the sample API."""

import hmac
import hashlib
import time
from typing import Optional

SECRET_KEY = "dev-secret-change-in-prod"
TOKEN_TTL_SECONDS = 3600


def generate_token(user_id: str) -> str:
    """Create a time-limited HMAC token for a given user."""
    expiry    = int(time.time()) + TOKEN_TTL_SECONDS
    payload   = f"{user_id}:{expiry}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def validate_token(token: str) -> Optional[str]:
    """
    Validate a token and return the user_id if valid, else None.
    Returns None if the token is malformed, expired, or tampered with.
    """
    try:
        user_id, expiry_str, signature = token.rsplit(":", 2)
    except ValueError:
        return None

    expiry = int(expiry_str)
    if time.time() > expiry:
        return None

    expected_payload   = f"{user_id}:{expiry}"
    expected_signature = hmac.new(SECRET_KEY.encode(), expected_payload.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return None

    return user_id


def require_auth(token: str) -> str:
    """Decorator-style guard. Raises ValueError if token is invalid."""
    user_id = validate_token(token)
    if user_id is None:
        raise ValueError("Unauthorized: invalid or expired token")
    return user_id
