"""Unit tests for JWT claim validation helpers."""

import pytest
from jose import JWTError

from app.core.token_validation import extract_token_version, validate_token_claims


def test_extract_token_version_success() -> None:
    assert extract_token_version({"tv": 3}) == 3


@pytest.mark.parametrize("payload", [{}, {"tv": None}, {"tv": "1"}, {"tv": -1}, {"tv": True}])
def test_extract_token_version_rejects_invalid(payload: dict) -> None:
    with pytest.raises(JWTError):
        extract_token_version(payload)


def test_validate_token_claims_returns_subject() -> None:
    subject = validate_token_claims(
        {"type": "access", "sub": "550e8400-e29b-41d4-a716-446655440000"},
        expected_type="access",
    )
    assert subject == "550e8400-e29b-41d4-a716-446655440000"
