"""Test-only AuthService that seeds organization membership on doctor registration."""

from uuid import uuid4

from app.application.services.auth_service import AuthService
from app.application.dtos.user import UserDTO
from app.domain.entities.user import UserRole
from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)


class AuthServiceWithDoctorMembership(AuthService):
    """Ensures self-registered doctors can create org-scoped patients in API tests."""

    def __init__(
        self,
        user_repository,
        settings,
        audit_service,
        membership_repository: InMemoryOrganizationMembershipRepository,
    ) -> None:
        super().__init__(user_repository, settings, audit_service)
        self._memberships = membership_repository

    async def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.PATIENT,
    ) -> UserDTO:
        user = await super().register(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        if role == UserRole.DOCTOR:
            await self._memberships.create(
                OrganizationMembership(
                    organization_id=uuid4(),
                    user_id=user.id,
                    membership_role=OrganizationMembershipRole.DOCTOR,
                    status=MembershipStatus.ACTIVE,
                ),
            )
        return user
