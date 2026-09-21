"""Shared JWT claim validation helpers."""

from __future__ import annotations

from typing import Any

from jose import JWTError


def validate_token_claims(payload: dict[str, Any], *, expected_type: str) -> str:
    """Validate token type and subject claims. Returns the subject string."""
    token_type = payload.get("type")
    if token_type != expected_type:
        raise JWTError("Invalid token type")

    subject = payload.get("sub")
    if subject is None:
        raise JWTError("Invalid token payload")

    return str(subject)


def extract_token_version(payload: dict[str, Any]) -> int:
    """Return the token version claim used for server-side revocation."""
    if "tv" not in payload:
        raise JWTError("Invalid token payload")

    token_version = payload["tv"]
    if isinstance(token_version, bool) or not isinstance(token_version, int):
        raise JWTError("Invalid token payload")

    if token_version < 0:
        raise JWTError("Invalid token payload")

    return token_version
