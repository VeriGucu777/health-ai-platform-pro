"""Seed active doctor organization membership for patient write policy tests."""

from uuid import UUID, uuid4

from httpx import AsyncClient

from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)


async def seed_doctor_membership_for_headers(
    client: AsyncClient,
    headers: dict[str, str],
    membership_repository: InMemoryOrganizationMembershipRepository,
    *,
    organization_id: UUID | None = None,
) -> UUID:
    """Ensure the bearer user has a single active DOCTOR membership in organization_id."""
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    user_id = me.json()["id"]
    org_id = organization_id or uuid4()
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=user_id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    return org_id
