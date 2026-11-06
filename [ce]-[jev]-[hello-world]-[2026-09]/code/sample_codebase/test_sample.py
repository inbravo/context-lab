"""test_sample.py — Minimal tests for the sample codebase."""

import time
from auth import generate_token, validate_token


def test_valid_token():
    token   = generate_token("user_42")
    user_id = validate_token(token)
    assert user_id == "user_42"


def test_expired_token():
    import hmac, hashlib
    SECRET_KEY = "dev-secret-change-in-prod"
    expiry     = int(time.time()) - 1          # already expired
    payload    = f"user_42:{expiry}"
    sig        = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token      = f"{payload}:{sig}"
    assert validate_token(token) is None


def test_tampered_token():
    token   = generate_token("user_42")
    tampered = token[:-4] + "xxxx"
    assert validate_token(tampered) is None


def test_malformed_token():
    assert validate_token("not-a-valid-token") is None
