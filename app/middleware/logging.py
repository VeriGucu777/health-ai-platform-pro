"""Request logging middleware."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.request_context import (
    clear_request_context,
    is_valid_request_id,
    resolve_request_id,
    set_request_context,
)
from app.observability.metrics import record_http_request

logger = get_logger(__name__)


def _resolve_route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


def _truncate_client_key(client_key: str) -> str:
    if client_key == "unknown":
        return client_key
    if ":" in client_key:
        return "ipv6:[redacted]"
    parts = client_key.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    return "[redacted]"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request metadata, bind correlation ids, and record optional metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inbound_request_id = request.headers.get("X-Request-ID")
        inbound_correlation_id = request.headers.get("X-Correlation-ID")
        request_id = resolve_request_id(inbound_request_id)
        correlation_id = (
            inbound_correlation_id.strip()
            if is_valid_request_id(inbound_correlation_id)
            else None
        )
        set_request_context(request_id=request_id, correlation_id=correlation_id)
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            duration_seconds = duration_ms / 1000
            status_code = response.status_code if response is not None else 500
            path_template = _resolve_route_template(request)
            settings: Settings = request.app.state.settings

            logger.info(
                "%s %s → %s (%.1fms) [%s]",
                request.method,
                path_template,
                status_code,
                duration_ms,
                request_id,
                extra={
                    "method": request.method,
                    "path_template": path_template,
                    "status_code": status_code,
                },
            )

            if settings.slow_request_threshold_ms > 0 and duration_ms >= settings.slow_request_threshold_ms:
                logger.warning(
                    "Slow request %s %s took %.1fms [%s]",
                    request.method,
                    path_template,
                    duration_ms,
                    request_id,
                    extra={
                        "method": request.method,
                        "path_template": path_template,
                        "status_code": status_code,
                    },
                )

            record_http_request(
                method=request.method,
                path_template=path_template,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )

            if response is not None:
                response.headers["X-Request-ID"] = request_id
                if correlation_id is not None:
                    response.headers["X-Correlation-ID"] = correlation_id

            clear_request_context()


def truncate_client_ip_for_audit(client_key: str) -> str:
    """Return a privacy-safe client key for security audit logs."""
    return _truncate_client_key(client_key)
