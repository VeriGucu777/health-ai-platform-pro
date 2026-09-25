"""SQLAlchemy user repository."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_repository import UserRepository as UserRepositoryPort
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


def normalize_email(email: str) -> str:
    """Normalize email for storage and lookup."""
    return email.strip().lower()


class SQLAlchemyUserRepository(SQLAlchemyRepository[UserModel, User], UserRepositoryPort):
    """PostgreSQL-backed user repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    async def get_by_email(self, email: str) -> User | None:
        normalized = normalize_email(email)
        stmt = select(UserModel).where(func.lower(UserModel.email) == normalized)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def email_exists(self, email: str) -> bool:
        user = await self.get_by_email(email)
        return user is not None

    async def increment_token_version(self, user_id: UUID) -> User:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(token_version=UserModel.token_version + 1)
            .returning(UserModel)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            msg = "User not found"
            raise ValueError(msg)
        return self._to_entity(model)

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            first_name=model.first_name,
            last_name=model.last_name,
            role=UserRole(model.role),
            is_active=model.is_active,
            is_verified=model.is_verified,
            email_verified_at=model.email_verified_at,
            token_version=model.token_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=normalize_email(entity.email),
            hashed_password=entity.hashed_password,
            first_name=entity.first_name,
            last_name=entity.last_name,
            role=entity.role,
            is_active=entity.is_active,
            is_verified=entity.is_verified,
            email_verified_at=entity.email_verified_at,
            token_version=entity.token_version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
