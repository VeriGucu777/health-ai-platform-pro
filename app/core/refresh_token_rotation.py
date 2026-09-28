"""Refresh token rotation helpers (store HMAC digest of jti only — never the raw token)."""

from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4

from app.core.config import Settings


def new_refresh_jti() -> str:
    return str(uuid4())


def hash_refresh_jti(*, jti: str, settings: Settings) -> str:
    """Return a stable hex digest for persistence (not reversible to jti without secret)."""
    key = settings.jwt_secret_key.encode("utf-8")
    msg = jti.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
