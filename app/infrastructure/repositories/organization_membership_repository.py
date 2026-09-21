"""SQLAlchemy organization membership repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.organization_membership_repository import (
    OrganizationMembershipRepository as OrganizationMembershipRepositoryPort,
)
from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.models.organization_membership import OrganizationMembershipModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyOrganizationMembershipRepository(
    SQLAlchemyRepository[OrganizationMembershipModel, OrganizationMembership],
    OrganizationMembershipRepositoryPort,
):
    """PostgreSQL-backed organization membership repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationMembershipModel)

    async def list_active_organization_ids_for_user(self, user_id: UUID) -> list[UUID]:
        stmt = select(OrganizationMembershipModel.organization_id).where(
            OrganizationMembershipModel.user_id == user_id,
            OrganizationMembershipModel.status == MembershipStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_memberships_for_user(
        self,
        user_id: UUID,
        *,
        membership_role: OrganizationMembershipRole | None = None,
    ) -> list[OrganizationMembership]:
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.user_id == user_id,
            OrganizationMembershipModel.status == MembershipStatus.ACTIVE.value,
        )
        if membership_role is not None:
            stmt = stmt.where(
                OrganizationMembershipModel.membership_role == membership_role.value,
            )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def list_active_doctor_memberships_in_organization(
        self,
        organization_id: UUID,
    ) -> list[OrganizationMembership]:
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.organization_id == organization_id,
            OrganizationMembershipModel.status == MembershipStatus.ACTIVE.value,
            OrganizationMembershipModel.membership_role == OrganizationMembershipRole.DOCTOR.value,
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def get_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMembership | None:
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.organization_id == organization_id,
            OrganizationMembershipModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: OrganizationMembershipModel) -> OrganizationMembership:
        return OrganizationMembership(
            id=model.id,
            organization_id=model.organization_id,
            user_id=model.user_id,
            membership_role=OrganizationMembershipRole(model.membership_role),
            status=MembershipStatus(model.status),
            joined_at=model.joined_at,
            left_at=model.left_at,
        )

    def _to_model(self, entity: OrganizationMembership) -> OrganizationMembershipModel:
        return OrganizationMembershipModel(
            id=entity.id,
            organization_id=entity.organization_id,
            user_id=entity.user_id,
            membership_role=entity.membership_role,
            status=entity.status,
            joined_at=entity.joined_at,
            left_at=entity.left_at,
        )
