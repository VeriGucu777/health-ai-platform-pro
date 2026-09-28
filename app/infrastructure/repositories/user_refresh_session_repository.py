"""SQLAlchemy refresh session repository."""

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user_refresh_session import UserRefreshSession
from app.domain.interfaces.user_refresh_session_repository import (
    UserRefreshSessionRepository as UserRefreshSessionRepositoryPort,
)
from app.infrastructure.database.models.user_refresh_session import UserRefreshSessionModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyUserRefreshSessionRepository(
    SQLAlchemyRepository[UserRefreshSessionModel, UserRefreshSession],
    UserRefreshSessionRepositoryPort,
):
    """PostgreSQL-backed refresh session store."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserRefreshSessionModel)

    async def get_by_hash(self, refresh_token_id_hash: str) -> UserRefreshSession | None:
        stmt = select(UserRefreshSessionModel).where(
            UserRefreshSessionModel.refresh_token_id_hash == refresh_token_id_hash,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create_session(
        self,
        user_id: UUID,
        refresh_token_id_hash: str,
    ) -> UserRefreshSession:
        entity = UserRefreshSession(
            user_id=user_id,
            refresh_token_id_hash=refresh_token_id_hash,
        )
        return await self.create(entity)

    async def rotate_hash(self, session_id: UUID, refresh_token_id_hash: str) -> None:
        stmt = (
            update(UserRefreshSessionModel)
            .where(UserRefreshSessionModel.id == session_id)
            .values(refresh_token_id_hash=refresh_token_id_hash)
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = delete(UserRefreshSessionModel).where(UserRefreshSessionModel.user_id == user_id)
        await self._session.execute(stmt)

    def _to_entity(self, model: UserRefreshSessionModel) -> UserRefreshSession:
        return UserRefreshSession(
            id=model.id,
            user_id=model.user_id,
            refresh_token_id_hash=model.refresh_token_id_hash,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: UserRefreshSession) -> UserRefreshSessionModel:
        return UserRefreshSessionModel(
            id=entity.id,
            user_id=entity.user_id,
            refresh_token_id_hash=entity.refresh_token_id_hash,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
