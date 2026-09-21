"""Pilot runtime worker / rate-limit constraints."""

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.core.pilot_runtime import validate_pilot_runtime_settings


def test_pilot_allows_multi_worker_when_rate_limits_disabled() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="x" * 32,
        UVICORN_WORKERS=4,
        AUTH_RATE_LIMIT_ENABLED=False,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=False,
    )
    validate_pilot_runtime_settings(settings)


def test_pilot_rejects_multi_worker_with_auth_rate_limit() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="x" * 32,
        UVICORN_WORKERS=2,
        AUTH_RATE_LIMIT_ENABLED=True,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=False,
    )
    with pytest.raises(ConfigurationError, match="UVICORN_WORKERS must be 1"):
        validate_pilot_runtime_settings(settings)


def test_pilot_rejects_multi_worker_with_narrative_rate_limit() -> None:
    settings = Settings(
        ENVIRONMENT="staging",
        JWT_SECRET_KEY="x" * 32,
        UVICORN_WORKERS=3,
        AUTH_RATE_LIMIT_ENABLED=False,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=True,
    )
    with pytest.raises(ConfigurationError, match="AuthRateLimiter"):
        validate_pilot_runtime_settings(settings)


def test_development_skips_worker_validation() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        UVICORN_WORKERS=8,
        AUTH_RATE_LIMIT_ENABLED=True,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=True,
    )
    validate_pilot_runtime_settings(settings)
