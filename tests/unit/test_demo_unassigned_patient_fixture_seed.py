"""Unit tests for demo unassigned patient fixture seed."""

import pytest

from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.application.seeding.demo_organization_fixture_seed import (
    DemoOrganizationFixtureSeedConfig,
    seed_demo_organization_fixtures,
)
from app.application.seeding.demo_unassigned_patient_fixture_seed import (
    DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
    DemoUnassignedPatientFixtureSeedConfig,
    seed_demo_unassigned_patient_fixture,
)
from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import Organization, OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_user_repository import InMemoryUserRepository


async def _seed_admin_and_org(
    users: InMemoryUserRepository,
    orgs: InMemoryOrganizationRepository,
    memberships: InMemoryOrganizationMembershipRepository,
) -> tuple[Organization, User]:
    org = await orgs.create(
        Organization(name="Demo Clinic", slug=DEMO_ORGANIZATION_SLUG, is_active=True),
    )
    admin = await users.create(
        User(
            email="admin-unassigned@example.com",
            hashed_password=hash_password("SecurePass123!"),
            first_name="Clinic",
            last_name="Admin",
            role=UserRole.CLINIC_ADMIN,
        ),
    )
    await memberships.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    return org, admin


@pytest.mark.asyncio
async def test_unassigned_fixture_creates_patient_without_assignment() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)

    config = DemoUnassignedPatientFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
    )
    result = await seed_demo_unassigned_patient_fixture(
        user_repository=users,
        organization_repository=orgs,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )

    assert result.created_patient is True
    patient = await patients.get_by_id(result.patient_id)
    assert patient is not None
    assert patient.organization_id == org.id
    assert patient.notes == DEMO_UNASSIGNED_PATIENT_SEED_MARKER
    assert await assignments.list_by_patient_and_organization(patient.id, org.id) == []


@pytest.mark.asyncio
async def test_unassigned_fixture_seed_is_idempotent() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)
    config = DemoUnassignedPatientFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
    )

    first = await seed_demo_unassigned_patient_fixture(
        user_repository=users,
        organization_repository=orgs,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )
    second = await seed_demo_unassigned_patient_fixture(
        user_repository=users,
        organization_repository=orgs,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )

    assert first.patient_id == second.patient_id
    assert second.created_patient is False
    assert len(await patients.list_by_organization_ids([org.id], limit=100)) == 1


@pytest.mark.asyncio
async def test_doctor_sees_only_assigned_patient_when_both_fixtures_exist() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)
    doctor = await users.create(
        User(
            email="doctor-rbac-negative@example.com",
            hashed_password=hash_password("SecurePass123!"),
            first_name="Demo",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )

    assigned_config = DemoOrganizationFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        demo_doctor_email=doctor.email,
    )
    assigned = await seed_demo_organization_fixtures(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
        config=assigned_config,
    )

    unassigned_config = DemoUnassignedPatientFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
    )
    unassigned = await seed_demo_unassigned_patient_fixture(
        user_repository=users,
        organization_repository=orgs,
        patient_repository=patients,
        assignment_repository=assignments,
        config=unassigned_config,
    )

    assert assigned.patient_id != unassigned.patient_id
    visible = await patients.list_visible_to_doctor(doctor.id)
    assert len(visible) == 1
    assert visible[0].id == assigned.patient_id

    org_patients = await patients.list_by_organization_ids([org.id], limit=100)
    assert len(org_patients) == 2
