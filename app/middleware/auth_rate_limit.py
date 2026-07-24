"""In-memory rate limiting for sensitive authentication endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import RateLimitExceededError


class AuthRateLimiter:
    """Process-local sliding-window limiter keyed by endpoint scope and client IP."""

    def __init__(self) -> None:
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)

    def reset(self) -> None:
        """Clear all counters — useful for deterministic tests."""
        self._requests.clear()

    def check(self, *, scope: str, client_key: str, max_requests: int, window_seconds: int) -> None:
        """Raise RateLimitExceededError when the client exceeds the configured limit."""
        if max_requests <= 0:
            return

        now = time.monotonic()
        key = (scope, client_key)
        window_start = now - window_seconds
        recent = [timestamp for timestamp in self._requests[key] if timestamp > window_start]

        if len(recent) >= max_requests:
            raise RateLimitExceededError()

        recent.append(now)
        self._requests[key] = recent


def get_client_ip(request: Request) -> str:
    """Resolve the best-effort client IP for rate limiting."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def auth_rate_limit(scope: str) -> Callable[..., None]:
    """Dependency factory that enforces auth endpoint rate limits."""

    async def _enforce(request: Request) -> None:
        settings: Settings = request.app.state.settings
        if not settings.auth_rate_limit_enabled:
            return

        limiter: AuthRateLimiter = request.app.state.auth_rate_limiter
        limits = _limits_for_scope(settings, scope)
        limiter.check(
            scope=scope,
            client_key=get_client_ip(request),
            max_requests=limits[0],
            window_seconds=limits[1],
        )

    return _enforce


def _limits_for_scope(settings: Settings, scope: str) -> tuple[int, int]:
    if scope == "login":
        return settings.auth_login_rate_limit, settings.auth_login_rate_window_seconds
    if scope == "refresh":
        return settings.auth_refresh_rate_limit, settings.auth_refresh_rate_window_seconds
    if scope == "register":
        return settings.auth_register_rate_limit, settings.auth_register_rate_window_seconds
    return settings.auth_login_rate_limit, settings.auth_login_rate_window_seconds
