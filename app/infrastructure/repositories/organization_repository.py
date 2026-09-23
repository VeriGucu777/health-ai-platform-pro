"""SQLAlchemy organization repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.organization_repository import OrganizationRepository as OrganizationRepositoryPort
from app.domain.organization.entities import Organization
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyOrganizationRepository(
    SQLAlchemyRepository[OrganizationModel, Organization],
    OrganizationRepositoryPort,
):
    """PostgreSQL-backed organization repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationModel)

    async def get_by_slug(self, slug: str) -> Organization | None:
        normalized = slug.strip()
        if not normalized:
            return None
        stmt = select(OrganizationModel).where(OrganizationModel.slug == normalized)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: OrganizationModel) -> Organization:
        return Organization(
            id=model.id,
            name=model.name,
            slug=model.slug,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Organization) -> OrganizationModel:
        return OrganizationModel(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
