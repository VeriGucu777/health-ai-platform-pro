"""Generic SQLAlchemy repository base — extend for each entity."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.base import BaseEntity
from app.domain.interfaces.repository import Repository
from app.infrastructure.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)
EntityT = TypeVar("EntityT", bound=BaseEntity)


class SQLAlchemyRepository(Repository[EntityT], Generic[ModelT, EntityT]):
    """Base SQLAlchemy repository — maps ORM models to domain entities.

    Subclasses must implement _to_entity() and _to_model() mappers.
    """

    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    async def get_by_id(self, entity_id: UUID) -> EntityT | None:
        result = await self._session.get(self._model_class, entity_id)
        return self._to_entity(result) if result else None

    async def create(self, entity: EntityT) -> EntityT:
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: EntityT) -> EntityT:
        model = self._to_model(entity)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return self._to_entity(merged)

    async def delete(self, entity_id: UUID) -> bool:
        instance = await self._session.get(self._model_class, entity_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        return True

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[EntityT]:
        stmt = select(self._model_class).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    def _to_entity(self, model: ModelT) -> EntityT:
        raise NotImplementedError

    def _to_model(self, entity: EntityT) -> ModelT:
        raise NotImplementedError
