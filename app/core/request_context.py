"""Request-scoped identifiers for logging and error correlation."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_VALID_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def is_valid_request_id(value: str | None) -> bool:
    """Return True when an inbound request/correlation id is safe to reuse."""
    if value is None:
        return False
    candidate = value.strip()
    if not candidate or len(candidate) > 64:
        return False
    return _VALID_ID_PATTERN.fullmatch(candidate) is not None


def resolve_request_id(inbound: str | None) -> str:
    """Use a validated inbound id or generate a new UUID."""
    if inbound is not None and is_valid_request_id(inbound):
        return inbound.strip()
    return str(uuid.uuid4())


def set_request_context(*, request_id: str, correlation_id: str | None = None) -> None:
    """Bind identifiers to the current async context."""
    _REQUEST_ID.set(request_id)
    _CORRELATION_ID.set(correlation_id)


def clear_request_context() -> None:
    """Reset identifiers after a request completes."""
    _REQUEST_ID.set(None)
    _CORRELATION_ID.set(None)


def get_request_id() -> str | None:
    """Return the active request id, if any."""
    return _REQUEST_ID.get()


def get_correlation_id() -> str | None:
    """Return the active correlation id, if any."""
    return _CORRELATION_ID.get()
