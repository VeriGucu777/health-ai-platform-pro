"""Unit tests for demo clinic admin seed idempotency."""

import pytest

from app.application.seeding.demo_clinic_admin_seed import (
    DemoClinicAdminSeedConfig,
    seed_demo_clinic_admin,
)
from app.core.security import verify_password
from app.domain.entities.user import UserRole
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from tests.support.memory_organization_membership_repository import InMemoryOrganizationMembershipRepository
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_seed_creates_user_organization_and_membership() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    config = DemoClinicAdminSeedConfig(
        email="seed-ca@example.com",
        password="SecurePass123!",
        organization_slug="seed-demo-clinic",
    )

    result = await seed_demo_clinic_admin(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        config=config,
    )

    assert result.created_user is True
    assert result.created_organization is True
    assert result.created_membership is True

    user = await users.get_by_email(config.email)
    assert user is not None
    assert user.role == UserRole.CLINIC_ADMIN
    assert verify_password(config.password, user.hashed_password)

    org = await orgs.get_by_slug(config.organization_slug)
    assert org is not None
    assert org.id == result.organization_id

    membership = await memberships.get_by_organization_and_user(org.id, user.id)
    assert membership is not None
    assert membership.membership_role == OrganizationMembershipRole.CLINIC_ADMIN
    assert membership.status == MembershipStatus.ACTIVE


@pytest.mark.asyncio
async def test_seed_is_idempotent_on_second_run() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    config = DemoClinicAdminSeedConfig(
        email="seed-idempotent@example.com",
        password="SecurePass123!",
        organization_slug="seed-idempotent-clinic",
    )

    first = await seed_demo_clinic_admin(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        config=config,
    )
    second = await seed_demo_clinic_admin(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        config=config,
    )

    assert first.user_id == second.user_id
    assert first.organization_id == second.organization_id
    assert second.created_user is False
    assert second.created_organization is False
    assert second.created_membership is False
    assert len(users._users) == 1
    assert len(orgs._organizations) == 1
    assert len(memberships._memberships) == 1
