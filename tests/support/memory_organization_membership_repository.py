"""In-memory organization membership repository for policy tests."""

from uuid import UUID

from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole


class InMemoryOrganizationMembershipRepository(OrganizationMembershipRepository):
    """Stores memberships keyed by (organization_id, user_id)."""

    def __init__(self) -> None:
        self._memberships: dict[tuple[UUID, UUID], OrganizationMembership] = {}

    async def get_by_id(self, entity_id: UUID) -> OrganizationMembership | None:
        for membership in self._memberships.values():
            if membership.id == entity_id:
                return membership
        return None

    async def get_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMembership | None:
        return self._memberships.get((organization_id, user_id))

    async def list_active_organization_ids_for_user(self, user_id: UUID) -> list[UUID]:
        return [
            membership.organization_id
            for membership in self._memberships.values()
            if membership.user_id == user_id and membership.status == MembershipStatus.ACTIVE
        ]

    async def list_active_memberships_for_user(
        self,
        user_id: UUID,
        *,
        membership_role: OrganizationMembershipRole | None = None,
    ) -> list[OrganizationMembership]:
        items = [
            membership
            for membership in self._memberships.values()
            if membership.user_id == user_id and membership.status == MembershipStatus.ACTIVE
        ]
        if membership_role is not None:
            items = [m for m in items if m.membership_role == membership_role]
        return items

    async def list_active_doctor_memberships_in_organization(
        self,
        organization_id: UUID,
    ) -> list[OrganizationMembership]:
        return [
            membership
            for membership in self._memberships.values()
            if membership.organization_id == organization_id
            and membership.status == MembershipStatus.ACTIVE
            and membership.membership_role == OrganizationMembershipRole.DOCTOR
        ]

    async def create(self, entity: OrganizationMembership) -> OrganizationMembership:
        self._memberships[(entity.organization_id, entity.user_id)] = entity
        return entity

    async def update(self, entity: OrganizationMembership) -> OrganizationMembership:
        self._memberships[(entity.organization_id, entity.user_id)] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        for key, membership in list(self._memberships.items()):
            if membership.id == entity_id:
                del self._memberships[key]
                return True
        return False
