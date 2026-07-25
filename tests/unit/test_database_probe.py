"""Unit tests for the database connectivity probe."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.health.database_probe import check_database_connectivity


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
    engine.connect.side_effect = RuntimeError("connection refused")

    assert await check_database_connectivity(engine, timeout_seconds=1.0) is False
