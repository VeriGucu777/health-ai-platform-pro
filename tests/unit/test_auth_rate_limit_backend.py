"""Unit tests for authentication rate limiter backends."""

import pytest

from app.core.exceptions import RateLimitExceededError
from app.middleware.auth_rate_limit_backend import (
    MemoryAuthRateLimiterBackend,
    create_auth_rate_limiter_backend,
)


def test_memory_backend_blocks_after_limit() -> None:
    limiter = MemoryAuthRateLimiterBackend()
    for _ in range(2):
        limiter.check(scope="login", client_key="127.0.0.1", max_requests=2, window_seconds=60)

    with pytest.raises(RateLimitExceededError):
        limiter.check(scope="login", client_key="127.0.0.1", max_requests=2, window_seconds=60)


def test_create_backend_uses_memory_when_configured() -> None:
    backend = create_auth_rate_limiter_backend(
        backend="memory",
        redis_url=None,
        allow_memory_fallback=True,
    )
    assert isinstance(backend, MemoryAuthRateLimiterBackend)


def test_create_backend_falls_back_to_memory_without_redis_url_in_dev() -> None:
    backend = create_auth_rate_limiter_backend(
        backend="redis",
        redis_url=None,
        allow_memory_fallback=True,
    )
    assert isinstance(backend, MemoryAuthRateLimiterBackend)


def test_create_backend_requires_redis_url_without_fallback() -> None:
    with pytest.raises(ValueError, match="REDIS_URL is required"):
        create_auth_rate_limiter_backend(
            backend="redis",
            redis_url=None,
            allow_memory_fallback=False,
        )
