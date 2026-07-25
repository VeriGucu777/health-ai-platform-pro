"""Unit tests for integration database safety helpers."""

import pytest

from tests.integration.support.database import (
    assert_safe_integration_url,
    build_alembic_config,
    to_async_url,
    to_sync_url,
)

def test_blocked_production_database_name_is_rejected():
    with pytest.raises(RuntimeError, match="Refusing integration tests"):
        assert_safe_integration_url(
            "postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_platform",
        )


def test_testcontainers_style_url_is_allowed():
    assert_safe_integration_url("postgresql+psycopg://test:test@localhost:32768/test")


def test_url_conversion_helpers():
    raw = "postgresql+psycopg2://test:test@localhost:32768/test"
    sync_url = to_sync_url(raw)
    async_url = to_async_url(sync_url)
    assert sync_url.startswith("postgresql+psycopg://")
    assert async_url.startswith("postgresql+asyncpg://")


def test_alembic_config_uses_integration_database_url_attribute():
    sync_url = "postgresql+psycopg://test:test@localhost:32768/test"
    cfg = build_alembic_config(sync_url)
    assert cfg.attributes["integration_database_url"] == sync_url
