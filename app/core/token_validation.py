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
