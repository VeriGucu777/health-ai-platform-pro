"""Unit tests for production configuration guards."""

import pytest

from app.core.config import Settings, get_settings
from app.core.jwt_settings import validate_settings_security


def test_production_settings_reject_default_jwt_secret() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="change-me",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
    )
    with pytest.raises(ValueError, match="JWT_SECRET_KEY is missing, too short, or uses a default value"):
        validate_settings_security(settings)


def test_production_settings_accept_strong_jwt_secret() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
    )
    validate_settings_security(settings)
    assert settings.environment == "production"


def test_get_settings_rejects_insecure_production_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
    )

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        get_settings()

    get_settings.cache_clear()


def test_get_settings_accepts_production_env_with_strong_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a-unique-production-secret-with-sufficient-length")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://postgres:postgres@localhost:5432/health_ai_test",
    )

    settings = get_settings()
    assert settings.environment == "production"
    assert str(settings.database_url).startswith("postgresql+asyncpg://")

    get_settings.cache_clear()
