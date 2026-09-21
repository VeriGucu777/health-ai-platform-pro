"""Build auth audit context from incoming HTTP requests."""

from fastapi import Request

from app.application.dtos.auth_audit import AuthAuditContext
from app.core.request_context import get_request_id
from app.middleware.logging import truncate_client_ip_for_audit


def build_auth_audit_context(request: Request) -> AuthAuditContext:
    """Extract correlation and route metadata for auth audit events."""
    route = request.scope.get("route")
    route_template = getattr(route, "path", None) or request.url.path
    client_host = request.client.host if request.client is not None else "unknown"
    request_id = getattr(request.state, "request_id", None) or get_request_id()

    return AuthAuditContext(
        request_id=request_id,
        route_template=route_template,
        client_ip_truncated=truncate_client_ip_for_audit(client_host),
    )
