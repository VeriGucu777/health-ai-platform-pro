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
        DEBUG=False,
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        CORS_ORIGINS=["https://app.example.com"],
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
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("DEBUG", "false")

    settings = get_settings()
    assert settings.environment == "production"
    assert str(settings.database_url).startswith("postgresql+asyncpg://")

    get_settings.cache_clear()


def test_production_settings_reject_localhost_cors() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        CORS_ORIGINS=["http://localhost:3000"],
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
    )
    with pytest.raises(ValueError, match="CORS_ORIGINS must not include localhost"):
        validate_settings_security(settings)


def test_production_settings_reject_debug_enabled() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        CORS_ORIGINS=["https://app.example.com"],
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
    )
    with pytest.raises(ValueError, match="DEBUG must be false in production"):
        validate_settings_security(settings)


def test_default_cors_origins_include_standard_dev_hosts() -> None:
    settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins


def test_default_port_is_8001() -> None:
    settings = Settings(JWT_SECRET_KEY="test-secret-key-for-unit-tests-only")
    assert settings.port == 8001
