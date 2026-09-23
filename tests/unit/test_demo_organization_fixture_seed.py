"""Unit tests for demo organization fixture seed."""

from datetime import date

import pytest

from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.application.seeding.demo_organization_fixture_seed import (
    DEMO_PATIENT_SEED_MARKER,
    DemoOrganizationFixtureSeedConfig,
    seed_demo_organization_fixtures,
)
from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import Organization, OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.support.memory_organization_membership_repository import InMemoryOrganizationMembershipRepository
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
            email="admin-fixture@example.com",
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
async def test_fixture_seed_creates_doctor_membership_patient_and_assignment() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)
    doctor = await users.create(
        User(
            email="doctor-fixture@example.com",
            hashed_password=hash_password("SecurePass123!"),
            first_name="Demo",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )

    config = DemoOrganizationFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        demo_doctor_email=doctor.email,
    )

    result = await seed_demo_organization_fixtures(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )

    assert result.created_doctor_membership is True
    assert result.created_patient is True
    assert result.created_assignment is True

    doctor_membership = await memberships.get_by_organization_and_user(org.id, doctor.id)
    assert doctor_membership is not None
    assert doctor_membership.membership_role == OrganizationMembershipRole.DOCTOR

    patient = await patients.get_by_id(result.patient_id)
    assert patient is not None
    assert patient.organization_id == org.id
    assert patient.notes == DEMO_PATIENT_SEED_MARKER

    assignment = await assignments.get_by_patient_and_assignee(patient.id, doctor.id)
    assert assignment is not None
    assert assignment.status == AssignmentStatus.ACTIVE

    visible = await patients.list_visible_to_doctor(doctor.id)
    assert len(visible) == 1
    assert visible[0].id == patient.id


@pytest.mark.asyncio
async def test_fixture_seed_is_idempotent() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)
    doctor = await users.create(
        User(
            email="doctor-idem@example.com",
            hashed_password=hash_password("SecurePass123!"),
            first_name="Demo",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )
    config = DemoOrganizationFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        demo_doctor_email=doctor.email,
    )

    first = await seed_demo_organization_fixtures(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )
    second = await seed_demo_organization_fixtures(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )

    assert first.patient_id == second.patient_id
    assert second.created_doctor_membership is False
    assert second.created_patient is False
    assert second.created_assignment is False
    assert len(await patients.list_by_organization_ids([org.id], limit=100)) == 1


@pytest.mark.asyncio
async def test_fixture_seed_reuses_existing_patient_by_marker() -> None:
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin = await _seed_admin_and_org(users, orgs, memberships)
    doctor = await users.create(
        User(
            email="doctor-reuse@example.com",
            hashed_password=hash_password("SecurePass123!"),
            first_name="Demo",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )
    existing_patient = await patients.create(
        Patient(
            owner_id=admin.id,
            organization_id=org.id,
            first_name="Demo",
            last_name="Policy Patient",
            date_of_birth=date(1990, 6, 12),
            gender="female",
            notes=DEMO_PATIENT_SEED_MARKER,
        ),
    )

    config = DemoOrganizationFixtureSeedConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        demo_doctor_email=doctor.email,
    )
    result = await seed_demo_organization_fixtures(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
        config=config,
    )

    assert result.created_patient is False
    assert result.patient_id == existing_patient.id
