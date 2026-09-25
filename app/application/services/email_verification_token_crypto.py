"""Hashing helpers for email verification tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_raw_verification_token() -> str:
    """Return a URL-safe one-time verification token."""
    return secrets.token_urlsafe(32)


def hash_verification_token(raw_token: str, *, pepper: str) -> str:
    """Derive a stored hash from the raw token and server pepper."""
    if not pepper.strip():
        msg = "Email verification pepper must be configured"
        raise ValueError(msg)
    return hmac.new(
        pepper.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
