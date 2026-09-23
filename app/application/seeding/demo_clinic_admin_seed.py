"""Idempotent demo clinic admin seed — operations use only, not HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.user_repository import UserRepository
from app.domain.organization.entities import Organization, OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from app.infrastructure.repositories.user_repository import normalize_email


DEMO_CLINIC_ADMIN_EMAIL = "live-pa-admin-c45d9a48@example.com"
DEMO_CLINIC_ADMIN_PASSWORD = "LivePolicyE2E1!"
DEMO_CLINIC_ADMIN_FIRST_NAME = "Clinic"
DEMO_CLINIC_ADMIN_LAST_NAME = "Admin"
DEMO_ORGANIZATION_NAME = "Demo Live Policy Clinic"
DEMO_ORGANIZATION_SLUG = "demo-live-policy-clinic"


class OrganizationSeedRepository(Protocol):
    """Minimal organization persistence for demo seeding."""

    async def create(self, entity: Organization) -> Organization: ...

    async def get_by_slug(self, slug: str) -> Organization | None: ...


@dataclass(frozen=True)
class DemoClinicAdminSeedConfig:
    email: str = DEMO_CLINIC_ADMIN_EMAIL
    password: str = DEMO_CLINIC_ADMIN_PASSWORD
    first_name: str = DEMO_CLINIC_ADMIN_FIRST_NAME
    last_name: str = DEMO_CLINIC_ADMIN_LAST_NAME
    organization_name: str = DEMO_ORGANIZATION_NAME
    organization_slug: str = DEMO_ORGANIZATION_SLUG


@dataclass(frozen=True)
class DemoClinicAdminSeedResult:
    organization_id: UUID
    user_id: UUID
    created_organization: bool
    created_user: bool
    created_membership: bool


async def seed_demo_clinic_admin(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: OrganizationMembershipRepository,
    config: DemoClinicAdminSeedConfig | None = None,
) -> DemoClinicAdminSeedResult:
    """Ensure demo clinic admin user, organization, and active clinic_admin membership exist."""
    cfg = config or DemoClinicAdminSeedConfig()
    normalized_email = normalize_email(cfg.email)

    created_organization = False
    organization = await organization_repository.get_by_slug(cfg.organization_slug)
    if organization is None:
        organization = await organization_repository.create(
            Organization(
                name=cfg.organization_name,
                slug=cfg.organization_slug,
                is_active=True,
            ),
        )
        created_organization = True

    created_user = False
    user = await user_repository.get_by_email(normalized_email)
    if user is None:
        user = await user_repository.create(
            User(
                email=normalized_email,
                hashed_password=hash_password(cfg.password),
                first_name=cfg.first_name.strip(),
                last_name=cfg.last_name.strip(),
                role=UserRole.CLINIC_ADMIN,
                is_active=True,
                is_verified=True,
            ),
        )
        created_user = True
    elif user.role != UserRole.CLINIC_ADMIN:
        msg = (
            f"User {normalized_email} already exists with role {user.role.value}; "
            "refusing to change role via seed"
        )
        raise ValueError(msg)

    created_membership = False
    membership = await membership_repository.get_by_organization_and_user(
        organization.id,
        user.id,
    )
    if membership is None:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        )
        created_membership = True
    elif (
        membership.membership_role != OrganizationMembershipRole.CLINIC_ADMIN
        or membership.status != MembershipStatus.ACTIVE
    ):
        msg = (
            "Existing organization membership for demo admin is not an active clinic_admin; "
            "fix manually before re-running seed"
        )
        raise ValueError(msg)

    return DemoClinicAdminSeedResult(
        organization_id=organization.id,
        user_id=user.id,
        created_organization=created_organization,
        created_user=created_user,
        created_membership=created_membership,
    )
