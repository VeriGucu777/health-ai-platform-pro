"""Operational health and readiness aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import Settings
from app.infrastructure.database.session import get_engine
from app.infrastructure.health.database_probe import check_database_connectivity


@dataclass(frozen=True)
class ReadinessResult:
    """Outcome of dependency readiness checks."""

    is_ready: bool
    status: str
    checks: dict[str, str] = field(default_factory=dict)


class SystemHealthService:
    """Evaluate liveness metadata and dependency readiness."""

    def __init__(self, settings: Settings, *, started_at: datetime) -> None:
        self._settings = settings
        self._started_at = started_at

    @property
    def uptime_seconds(self) -> int:
        elapsed = datetime.now(UTC) - self._started_at
        return max(0, int(elapsed.total_seconds()))

    async def check_readiness(self) -> ReadinessResult:
        """Verify required dependencies before accepting traffic."""
        if not self._settings.health_check_db_enabled:
            return ReadinessResult(
                is_ready=True,
                status="ready",
                checks={"database": "skipped"},
            )

        engine = get_engine(self._settings)
        database_ok = await check_database_connectivity(
            engine,
            timeout_seconds=self._settings.health_check_db_timeout_seconds,
        )
        checks = {"database": "ok" if database_ok else "down"}
        if database_ok:
            return ReadinessResult(is_ready=True, status="ready", checks=checks)
        return ReadinessResult(is_ready=False, status="not_ready", checks=checks)
