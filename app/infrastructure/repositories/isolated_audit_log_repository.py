"""Audit log repository that commits in a dedicated database transaction."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository as AuditLogRepositoryPort
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.repositories.audit_log_repository import SQLAlchemyAuditLogRepository

SessionFactory = Callable[[], AsyncSession] | async_sessionmaker[AsyncSession]


class IsolatedSQLAlchemyAuditLogRepository(AuditLogRepositoryPort):
    """Append audit rows outside the request/business SQLAlchemy session."""

    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        self._session_factory = session_factory

    def _open_session(self) -> AsyncSession:
        factory = self._session_factory or get_session_factory()
        return factory()

    async def append(self, record: AuditLog) -> AuditLog:
        async with self._open_session() as session:
            try:
                inner = SQLAlchemyAuditLogRepository(session)
                created = await inner.append(record)
                await session.commit()
                return created
            except Exception:
                await session.rollback()
                raise
