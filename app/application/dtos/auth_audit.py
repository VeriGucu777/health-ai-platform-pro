"""Request context for authentication audit events."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthAuditContext:
    """HTTP metadata attached to auth audit records."""

    request_id: str | None
    route_template: str | None
    client_ip_truncated: str | None
