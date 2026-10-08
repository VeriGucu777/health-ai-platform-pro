"""Application transaction boundary (commit/rollback owned by use cases)."""

from typing import Protocol


class ApplicationTransaction(Protocol):
    """Unit-of-work boundary; infrastructure supplies session-backed impl."""

    async def commit(self) -> None:
        """Persist work from the current unit of work."""

    async def rollback(self) -> None:
        """Discard uncommitted work from the current unit of work."""
