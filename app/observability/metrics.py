"""Prometheus metrics (opt-in via METRICS_ENABLED)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import Counter, Histogram

_COUNTERS: dict[str, Counter] = {}
_HISTOGRAMS: dict[str, Histogram] = {}
_ENABLED = False


def configure_metrics(enabled: bool) -> None:
    """Initialize or disable Prometheus collectors."""
    global _ENABLED, _COUNTERS, _HISTOGRAMS
    _ENABLED = enabled
    if not enabled:
        _COUNTERS = {}
        _HISTOGRAMS = {}
        return

    from prometheus_client import Counter, Histogram

    _COUNTERS = {
        "http_requests_total": Counter(
            "http_requests_total",
            "Total HTTP requests processed",
            ["method", "path_template", "status"],
        ),
        "db_health_check_total": Counter(
            "db_health_check_total",
            "Database readiness probe results",
            ["result"],
        ),
        "auth_rate_limit_blocked_total": Counter(
            "auth_rate_limit_blocked_total",
            "Authentication rate limit blocks",
            ["scope"],
        ),
    }
    _HISTOGRAMS = {
        "http_request_duration_seconds": Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "path_template"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        ),
    }


def metrics_enabled() -> bool:
    """Return True when Prometheus metrics collection is active."""
    return _ENABLED


def record_http_request(
    *,
    method: str,
    path_template: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record HTTP request count and latency."""
    if not _ENABLED:
        return
    status = str(status_code)
    _COUNTERS["http_requests_total"].labels(method, path_template, status).inc()
    _HISTOGRAMS["http_request_duration_seconds"].labels(method, path_template).observe(
        duration_seconds,
    )


def record_db_health_check(*, success: bool) -> None:
    """Record a database readiness probe outcome."""
    if not _ENABLED:
        return
    result = "ok" if success else "fail"
    _COUNTERS["db_health_check_total"].labels(result).inc()


def record_auth_rate_limit_block(*, scope: str) -> None:
    """Record an authentication rate limit block."""
    if not _ENABLED:
        return
    _COUNTERS["auth_rate_limit_blocked_total"].labels(scope).inc()


def render_prometheus_metrics() -> tuple[bytes, str]:
    """Return Prometheus exposition format payload."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return generate_latest(), CONTENT_TYPE_LATEST
