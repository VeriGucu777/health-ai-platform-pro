"""Rate limiter backends for authentication endpoints."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict

from app.core.exceptions import RateLimitExceededError


class AuthRateLimiterBackend(ABC):
    """Common interface for auth endpoint rate limiters."""

    @abstractmethod
    def reset(self) -> None:
        """Clear counters — useful for deterministic tests."""

    @abstractmethod
    def check(
        self,
        *,
        scope: str,
        client_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Raise RateLimitExceededError when the client exceeds the configured limit."""


class MemoryAuthRateLimiterBackend(AuthRateLimiterBackend):
    """Process-local sliding-window limiter keyed by endpoint scope and client IP."""

    def __init__(self) -> None:
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._requests.clear()

    def check(
        self,
        *,
        scope: str,
        client_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
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


class RedisAuthRateLimiterBackend(AuthRateLimiterBackend):
    """Redis-backed fixed-window limiter shared across application instances."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)

    def reset(self) -> None:
        for key in self._client.scan_iter("auth_rate:*"):
            self._client.delete(key)

    def check(
        self,
        *,
        scope: str,
        client_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        if max_requests <= 0:
            return

        key = f"auth_rate:{scope}:{client_key}"
        count = int(self._client.incr(key))
        if count == 1:
            self._client.expire(key, window_seconds)

        if count > max_requests:
            raise RateLimitExceededError()


def create_auth_rate_limiter_backend(
    *,
    backend: str,
    redis_url: str | None,
    allow_memory_fallback: bool,
) -> AuthRateLimiterBackend:
    """Build the configured rate limiter backend with a safe in-memory fallback."""
    if backend == "memory":
        return MemoryAuthRateLimiterBackend()

    if backend == "redis":
        if not redis_url:
            if allow_memory_fallback:
                return MemoryAuthRateLimiterBackend()
            msg = "REDIS_URL is required when AUTH_RATE_LIMIT_BACKEND=redis"
            raise ValueError(msg)

        try:
            limiter = RedisAuthRateLimiterBackend(redis_url)
            limiter._client.ping()
            return limiter
        except Exception:
            if allow_memory_fallback:
                return MemoryAuthRateLimiterBackend()
            raise

    msg = f"Unsupported AUTH_RATE_LIMIT_BACKEND value: {backend}"
    raise ValueError(msg)
