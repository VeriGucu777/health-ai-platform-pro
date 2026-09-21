"""Organization membership repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.interfaces.repository import Repository
from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import OrganizationMembershipRole


class OrganizationMembershipRepository(Repository[OrganizationMembership]):
    """Contract for organization membership persistence."""

    @abstractmethod
    async def get_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMembership | None:
        """Return the membership row for the organization/user pair, any status."""

    @abstractmethod
    async def list_active_organization_ids_for_user(self, user_id: UUID) -> list[UUID]:
        """Return organization ids where the user has an active membership."""

    @abstractmethod
    async def list_active_memberships_for_user(
        self,
        user_id: UUID,
        *,
        membership_role: OrganizationMembershipRole | None = None,
    ) -> list[OrganizationMembership]:
        """Return active memberships for a user, optionally filtered by role."""

    @abstractmethod
    async def list_active_doctor_memberships_in_organization(
        self,
        organization_id: UUID,
    ) -> list[OrganizationMembership]:
        """Return active doctor-role memberships in an organization."""
