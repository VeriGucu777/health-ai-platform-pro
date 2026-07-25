"""Unit tests for request context helpers."""

import uuid

from app.core.request_context import (
    clear_request_context,
    get_correlation_id,
    get_request_id,
    is_valid_request_id,
    resolve_request_id,
    set_request_context,
)


def test_resolve_request_id_generates_uuid_when_missing() -> None:
    generated = resolve_request_id(None)
    uuid.UUID(generated)


def test_resolve_request_id_reuses_valid_inbound_value() -> None:
    inbound = "abc-123-valid"
    assert resolve_request_id(inbound) == inbound


def test_rejects_invalid_request_ids() -> None:
    assert is_valid_request_id("") is False
    assert is_valid_request_id("a" * 65) is False
    assert is_valid_request_id("invalid id") is False


def test_context_vars_round_trip() -> None:
    set_request_context(request_id="req-1", correlation_id="corr-1")
    assert get_request_id() == "req-1"
    assert get_correlation_id() == "corr-1"
    clear_request_context()
    assert get_request_id() is None
    assert get_correlation_id() is None
