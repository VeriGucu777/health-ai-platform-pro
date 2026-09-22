"""Unit tests for the database connectivity probe."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.engine import make_url

from app.infrastructure.health.database_probe import (
    _sanitize_probe_error_message,
    check_database_connectivity,
)


@pytest.mark.asyncio
async def test_check_database_connectivity_returns_true_on_success() -> None:
    connection = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 1
    connection.execute = AsyncMock(return_value=result)

    connect_cm = AsyncMock()
    connect_cm.__aenter__.return_value = connection
    connect_cm.__aexit__.return_value = None

    engine = MagicMock()
    engine.connect.return_value = connect_cm

    assert await check_database_connectivity(engine, timeout_seconds=1.0) is True


@pytest.mark.asyncio
async def test_check_database_connectivity_returns_false_on_failure() -> None:
    engine = MagicMock()
    engine.url = make_url("postgresql+asyncpg://appuser:secret-pass@db.internal:5432/health_ai")
    engine.connect.side_effect = RuntimeError("connection refused")

    assert await check_database_connectivity(engine, timeout_seconds=1.0) is False


def test_sanitize_probe_error_message_redacts_url_credentials() -> None:
    raw = (
        "could not connect: postgresql+asyncpg://appuser:secret-pass@db.internal:5432/health_ai"
    )
    sanitized = _sanitize_probe_error_message(raw)
    assert "secret-pass" not in sanitized
    assert "appuser:secret" not in sanitized
    assert "db.internal" in sanitized


@pytest.mark.asyncio
async def test_probe_failure_logs_without_secrets() -> None:
    engine = MagicMock()
    engine.url = make_url("postgresql+asyncpg://appuser:secret-pass@db.internal:5432/health_ai")
    engine.connect.side_effect = RuntimeError(
        "connection failed postgresql://appuser:secret-pass@db.internal:5432/health_ai",
    )

    with patch("app.infrastructure.health.database_probe.logger.warning") as mock_warning:
        ok = await check_database_connectivity(engine, timeout_seconds=1.0)

    assert ok is False
    mock_warning.assert_called_once()
    log_args = mock_warning.call_args[0]
    log_text = " ".join(str(part) for part in log_args)
    assert "Database readiness probe failed" in log_text
    assert "RuntimeError" in log_text
    assert "db.internal" in log_text
    assert "5432" in log_text
    assert "health_ai" in log_text
    assert "secret-pass" not in log_text
