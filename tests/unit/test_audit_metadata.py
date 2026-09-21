"""Audit metadata sanitization tests."""

import json

import pytest

from app.core.exceptions import ValidationError
from app.domain.audit.metadata import METADATA_MAX_BYTES, sanitize_audit_metadata


@pytest.mark.parametrize(
    "key",
    [
        "email",
        "password",
        "first_name",
        "phone",
        "notes",
        "token",
        "score",
        "probability",
        "body",
        "request",
        "response",
    ],
)
def test_forbidden_metadata_keys_are_rejected(key: str) -> None:
    with pytest.raises(ValidationError):
        sanitize_audit_metadata({key: "value"})


def test_unknown_metadata_keys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        sanitize_audit_metadata({"patient_name": "hidden"})


def test_allowlisted_metadata_is_sanitized() -> None:
    result = sanitize_audit_metadata(
        {
            "risk_kind": "diabetes",
            "page": 1,
            "page_size": 20,
            "include_risk_snapshot": True,
        }
    )
    assert result == {
        "risk_kind": "diabetes",
        "page": 1,
        "page_size": 20,
        "include_risk_snapshot": True,
    }


def test_metadata_size_limit_is_enforced() -> None:
    oversized = {"reason_code": "x" * (METADATA_MAX_BYTES + 50)}
    with pytest.raises(ValidationError):
        sanitize_audit_metadata(oversized)


def test_nested_metadata_is_rejected() -> None:
    with pytest.raises(ValidationError):
        sanitize_audit_metadata({"page": {"nested": True}})


def test_none_metadata_returns_none() -> None:
    assert sanitize_audit_metadata(None) is None


def test_serialized_metadata_stays_under_limit() -> None:
    metadata = sanitize_audit_metadata({"reason_code": "invalid_credentials"})
    assert metadata is not None
    assert len(json.dumps(metadata).encode("utf-8")) <= METADATA_MAX_BYTES
