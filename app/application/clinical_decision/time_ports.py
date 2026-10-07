"""Injectable time and evaluation id generation for deterministic tests."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4


class ClockPort(Protocol):
    def now_utc(self) -> datetime:
        """Return current UTC timestamp."""


class EvaluationIdFactoryPort(Protocol):
    def new_evaluation_id(self) -> UUID:
        """Return a new evaluation identifier."""


class SystemUtcClock:
    def now_utc(self) -> datetime:
        return datetime.now(UTC)


class UuidEvaluationIdFactory:
    def new_evaluation_id(self) -> UUID:
        return uuid4()
