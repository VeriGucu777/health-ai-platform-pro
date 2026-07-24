"""Unit tests for JWT secret configuration validation."""

import pytest

from app.core.config import Settings
from app.core.jwt_settings import validate_settings_security


def test_development_allows_default_jwt_secret() -> None:
    settings = Settings(ENVIRONMENT="development", JWT_SECRET_KEY="change-me")
    validate_settings_security(settings)
    assert settings.jwt_secret_key == "change-me"


def test_test_environment_allows_short_custom_secret() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )
    validate_settings_security(settings)
    assert settings.jwt_secret_key == "test-secret-key-for-unit-tests-only"


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_non_development_rejects_default_jwt_secret(environment: str) -> None:
    settings = Settings(ENVIRONMENT=environment, JWT_SECRET_KEY="change-me")
    with pytest.raises(ValueError, match="JWT_SECRET_KEY is missing, too short, or uses a default value"):
        validate_settings_security(settings)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_non_development_rejects_empty_jwt_secret(environment: str) -> None:
    settings = Settings(ENVIRONMENT=environment, JWT_SECRET_KEY="   ")
    with pytest.raises(ValueError):
        validate_settings_security(settings)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_non_development_rejects_short_jwt_secret(environment: str) -> None:
    settings = Settings(ENVIRONMENT=environment, JWT_SECRET_KEY="short-secret-value")
    with pytest.raises(ValueError):
        validate_settings_security(settings)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_non_development_accepts_strong_jwt_secret(environment: str) -> None:
    settings = Settings(
        ENVIRONMENT=environment,
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
    )
    validate_settings_security(settings)
    assert settings.environment == environment
