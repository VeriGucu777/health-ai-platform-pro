"""PostgreSQL connectivity probe for readiness checks."""

from __future__ import annotations

import asyncio
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger

logger = get_logger(__name__)

_URL_WITH_CREDS = re.compile(
    r"(postgres(?:ql)?(?:\+[\w]+)?://)([^\s/@]+)(@[^\s]+)",
    re.IGNORECASE,
)


def _sanitize_probe_error_message(message: str) -> str:
    """Strip credentials from driver error text before logging."""
    sanitized = _URL_WITH_CREDS.sub(r"\1***\3", message)
    sanitized = re.sub(r"(password=)[^\s&'\"]+", r"\1***", sanitized, flags=re.IGNORECASE)
    return sanitized[:500]


def _engine_connection_target(engine: AsyncEngine) -> tuple[str, int | str, str]:
    url = engine.url
    host = url.host or "unknown"
    port: int | str = url.port if url.port is not None else "unknown"
    database = url.database or "unknown"
    return host, port, database


async def check_database_connectivity(
    engine: AsyncEngine,
    *,
    timeout_seconds: float,
) -> bool:
    """Return True when a simple SELECT 1 succeeds within the timeout."""
    if timeout_seconds <= 0:
        timeout_seconds = 1.0

    host, port, database = _engine_connection_target(engine)

    async def _probe() -> bool:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar_one() == 1

    try:
        return await asyncio.wait_for(_probe(), timeout=timeout_seconds)
    except Exception as exc:
        logger.warning(
            "Database readiness probe failed (%s): %s [host=%s port=%s database=%s]",
            type(exc).__name__,
            _sanitize_probe_error_message(str(exc)),
            host,
            port,
            database,
        )
        return False
