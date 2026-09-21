"""Pilot/production runtime constraints (rate limits, workers)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ConfigurationError


def validate_pilot_runtime_settings(settings: Settings) -> None:
    """Enforce single-worker pilot when process-local rate limits are active."""
    if settings.environment not in ("production", "staging"):
        return

    workers = settings.uvicorn_workers
    if workers != 1:
        rate_limits_on = settings.auth_rate_limit_enabled or settings.clinical_narrative_rate_limit_enabled
        if rate_limits_on:
            raise ConfigurationError(
                "UVICORN_WORKERS must be 1 for pilot deployments while auth/clinical narrative "
                "rate limits use the in-process AuthRateLimiter (not shared across workers). "
                "Set UVICORN_WORKERS=1 or disable rate limits explicitly.",
            )
