"""Generic repository port — implement in infrastructure layer."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from app.domain.entities.base import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class Repository(ABC, Generic[T]):
    """Abstract repository defining CRUD operations for domain entities."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Retrieve an entity by its primary key."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity."""

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Remove an entity by ID. Returns True if deleted."""
