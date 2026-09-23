"""In-memory organization repository for seed unit tests."""

from uuid import UUID

from app.domain.interfaces.organization_repository import OrganizationRepository
from app.domain.organization.entities import Organization


class InMemoryOrganizationRepository(OrganizationRepository):
    """Stores organizations by id and unique slug."""

    def __init__(self) -> None:
        self._organizations: dict[UUID, Organization] = {}
        self._slug_index: dict[str, UUID] = {}

    async def get_by_id(self, entity_id: UUID) -> Organization | None:
        return self._organizations.get(entity_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        org_id = self._slug_index.get(slug.strip())
        if org_id is None:
            return None
        return self._organizations.get(org_id)

    async def create(self, entity: Organization) -> Organization:
        if entity.slug and entity.slug in self._slug_index:
            msg = f"Organization slug already exists: {entity.slug}"
            raise ValueError(msg)
        self._organizations[entity.id] = entity
        if entity.slug:
            self._slug_index[entity.slug] = entity.id
        return entity

    async def update(self, entity: Organization) -> Organization:
        if entity.id not in self._organizations:
            msg = "Organization not found"
            raise ValueError(msg)
        self._organizations[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        entity = self._organizations.pop(entity_id, None)
        if entity is None:
            return False
        if entity.slug and self._slug_index.get(entity.slug) == entity_id:
            del self._slug_index[entity.slug]
        return True
