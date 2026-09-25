"""Unit tests for demo live policy assignment repair seed."""

from datetime import date

import pytest

from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.application.seeding.demo_live_policy_repair import (
    repair_demo_live_policy_assignments,
    snapshot_demo_assignments,
)
from app.application.seeding.demo_organization_fixture_seed import DEMO_PATIENT_SEED_MARKER
from app.application.seeding.demo_unassigned_patient_fixture_seed import (
    DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
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


async def _seed_demo_context(
    *,
    users: InMemoryUserRepository,
    orgs: InMemoryOrganizationRepository,
    memberships: InMemoryOrganizationMembershipRepository,
    admin_email: str,
    doctor_email: str,
) -> tuple[Organization, User, User]:
    org = await orgs.create(
        Organization(name="Demo Clinic", slug=DEMO_ORGANIZATION_SLUG, is_active=True),
    )
    admin = await users.create(
        User(
            email=admin_email,
            hashed_password=hash_password("SecurePass123!"),
            first_name="Clinic",
            last_name="Admin",
            role=UserRole.CLINIC_ADMIN,
        ),
    )
    doctor = await users.create(
        User(
            email=doctor_email,
            hashed_password=hash_password("SecurePass123!"),
            first_name="Demo",
            last_name="Doctor",
            role=UserRole.DOCTOR,
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
    await memberships.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    return org, admin, doctor


@pytest.mark.asyncio
async def test_repair_reactivates_policy_and_deactivates_unassigned_for_doctor() -> None:
    from app.application.seeding.demo_clinic_admin_seed import DEMO_CLINIC_ADMIN_EMAIL
    from app.application.seeding.demo_organization_fixture_seed import (
        DEMO_DOCTOR_EMAIL,
        DEMO_PATIENT_DATE_OF_BIRTH,
        DEMO_PATIENT_FIRST_NAME,
        DEMO_PATIENT_LAST_NAME,
    )
    from app.application.seeding.demo_unassigned_patient_fixture_seed import (
        DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
        DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
        DEMO_UNASSIGNED_PATIENT_LAST_NAME,
    )

    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)

    org, admin, doctor = await _seed_demo_context(
        users=users,
        orgs=orgs,
        memberships=memberships,
        admin_email=DEMO_CLINIC_ADMIN_EMAIL,
        doctor_email=DEMO_DOCTOR_EMAIL,
    )

    policy_patient = await patients.create(
        Patient(
            first_name=DEMO_PATIENT_FIRST_NAME,
            last_name=DEMO_PATIENT_LAST_NAME,
            date_of_birth=DEMO_PATIENT_DATE_OF_BIRTH,
            gender="female",
            owner_id=admin.id,
            organization_id=org.id,
            notes=DEMO_PATIENT_SEED_MARKER,
        ),
    )
    unassigned_patient = await patients.create(
        Patient(
            first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
            last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
            date_of_birth=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
            gender="male",
            owner_id=admin.id,
            organization_id=org.id,
            notes=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
        ),
    )

    await assignments.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=policy_patient.id,
            assignee_user_id=doctor.id,
            is_primary=True,
            status=AssignmentStatus.INACTIVE,
            assigned_by_user_id=admin.id,
        ),
    )
    await assignments.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=unassigned_patient.id,
            assignee_user_id=doctor.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
            assigned_by_user_id=admin.id,
        ),
    )

    before_policy, before_unassigned = await snapshot_demo_assignments(
        patient_repository=patients,
        assignment_repository=assignments,
        organization_id=org.id,
        doctor_user_id=doctor.id,
    )
    assert before_policy.status == AssignmentStatus.INACTIVE.value
    assert before_unassigned.status == AssignmentStatus.ACTIVE.value

    result = await repair_demo_live_policy_assignments(
        user_repository=users,
        organization_repository=orgs,
        membership_repository=memberships,
        patient_repository=patients,
        assignment_repository=assignments,
    )

    assert result.policy_assignment_reactivated is True
    assert result.unassigned_assignments_deactivated == 1

    after_policy, after_unassigned = await snapshot_demo_assignments(
        patient_repository=patients,
        assignment_repository=assignments,
        organization_id=org.id,
        doctor_user_id=doctor.id,
    )
    assert after_policy.status == AssignmentStatus.ACTIVE.value
    assert after_unassigned.status == AssignmentStatus.INACTIVE.value
