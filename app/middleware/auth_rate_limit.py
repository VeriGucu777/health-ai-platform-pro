"""Rate limiting for sensitive authentication endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import RateLimitExceededError
from app.core.logging import get_logger, get_security_audit_logger
from app.middleware.auth_rate_limit_backend import (
    AuthRateLimiterBackend,
    MemoryAuthRateLimiterBackend,
    create_auth_rate_limiter_backend,
)
from app.middleware.logging import truncate_client_ip_for_audit
from app.observability.metrics import record_auth_rate_limit_block

_audit_logger = get_security_audit_logger()
_logger = get_logger(__name__)


class AuthRateLimiter:
    """Facade over memory or Redis rate limiter backends."""

    def __init__(self, backend: AuthRateLimiterBackend | None = None) -> None:
        self._backend = backend or MemoryAuthRateLimiterBackend()

    @classmethod
    def from_settings(cls, settings: Settings) -> "AuthRateLimiter":
        allow_fallback = settings.environment == "development"
        backend = create_auth_rate_limiter_backend(
            backend=settings.auth_rate_limit_backend,
            redis_url=settings.redis_url,
            allow_memory_fallback=allow_fallback,
        )
        if (
            settings.auth_rate_limit_backend == "redis"
            and settings.redis_url
            and isinstance(backend, MemoryAuthRateLimiterBackend)
            and allow_fallback
        ):
            _logger.warning(
                "Redis rate limiter unavailable; falling back to in-memory limiter for development",
            )
        return cls(backend)

    def reset(self) -> None:
        """Clear all counters — useful for deterministic tests."""
        self._backend.reset()

    def check(
        self,
        *,
        scope: str,
        client_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        self._backend.check(
            scope=scope,
            client_key=client_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )


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
        client_key = get_client_ip(request)
        try:
            limiter.check(
                scope=scope,
                client_key=client_key,
                max_requests=limits[0],
                window_seconds=limits[1],
            )
        except RateLimitExceededError:
            request_id = getattr(request.state, "request_id", None)
            _audit_logger.warning(
                "Auth rate limit exceeded scope=%s client=%s request_id=%s",
                scope,
                truncate_client_ip_for_audit(client_key),
                request_id,
            )
            record_auth_rate_limit_block(scope=scope)
            raise

    return _enforce


def _limits_for_scope(settings: Settings, scope: str) -> tuple[int, int]:
    if scope == "login":
        return settings.auth_login_rate_limit, settings.auth_login_rate_window_seconds
    if scope == "refresh":
        return settings.auth_refresh_rate_limit, settings.auth_refresh_rate_window_seconds
    if scope == "register":
        return settings.auth_register_rate_limit, settings.auth_register_rate_window_seconds
    return settings.auth_login_rate_limit, settings.auth_login_rate_window_seconds
