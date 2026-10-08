"""SQLAlchemy-backed application transaction boundary."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.clinical_encounter.transaction import ApplicationTransaction


class AsyncSessionApplicationTransaction:
    """Commits/rolls back the injected async session (repository flush-only)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
