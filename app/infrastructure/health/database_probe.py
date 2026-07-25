"""PostgreSQL connectivity probe for readiness checks."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def check_database_connectivity(
    engine: AsyncEngine,
    *,
    timeout_seconds: float,
) -> bool:
    """Return True when a simple SELECT 1 succeeds within the timeout."""
    if timeout_seconds <= 0:
        timeout_seconds = 1.0

    async def _probe() -> bool:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1

    try:
        return await asyncio.wait_for(_probe(), timeout=timeout_seconds)
    except Exception:
        return False
