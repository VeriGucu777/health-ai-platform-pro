"""JWT token creation and password hashing utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.token_validation import validate_token_claims


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a plain-text password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: str | Any,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
    *,
    token_version: int = 0,
) -> str:
    """Create a signed JWT access token."""
    settings = settings or get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "token_version": token_version,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str | Any,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    *,
    token_version: int = 0,
) -> str:
    """Create a signed JWT refresh token."""
    settings = settings or get_settings()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "token_version": token_version,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    settings = settings or get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_and_validate_token(
    token: str,
    *,
    expected_type: str,
    settings: Settings | None = None,
) -> str:
    """Decode a JWT and validate type/subject claims. Returns the subject."""
    payload = decode_token(token, settings)
    return validate_token_claims(payload, expected_type=expected_type)


__all__ = [
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_and_validate_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
