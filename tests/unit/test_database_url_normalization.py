"""Unit tests for DATABASE_URL normalization."""

import pytest

from app.core.config import Settings, normalize_database_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        (
            "postgres://user:pass@db.example.com:5432/mydb",
            "postgresql+asyncpg://user:pass@db.example.com:5432/mydb",
        ),
        (
            "postgresql://user:pass@db.example.com:5432/mydb",
            "postgresql+asyncpg://user:pass@db.example.com:5432/mydb",
        ),
        (
            "postgresql+asyncpg://user:pass@localhost:5432/health_ai_platform",
            "postgresql+asyncpg://user:pass@localhost:5432/health_ai_platform",
        ),
        (
            "postgres://user:p%40ss@host:5432/db?sslmode=require",
            "postgresql+asyncpg://user:p%40ss@host:5432/db?sslmode=require",
        ),
    ],
)
def test_normalize_database_url(raw_url: str, expected: str) -> None:
    assert normalize_database_url(raw_url) == expected


def test_settings_normalizes_postgres_scheme() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgres://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )
    assert str(settings.database_url).startswith("postgresql+asyncpg://")


def test_settings_normalizes_postgresql_scheme() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )
    assert str(settings.database_url).startswith("postgresql+asyncpg://")


def test_database_url_sync_uses_psycopg_driver() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgres://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
    )
    assert settings.database_url_sync.startswith("postgresql+psycopg://")
