"""Unit tests for DefaultPatientAccessPolicy."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_access_policy import PatientAccessAction
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.domain.patient_access.reason_codes import PatientAccessReasonCode
from tests.support.memory_organization_membership_repository import InMemoryOrganizationMembershipRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository


@pytest.fixture
def patient_repo() -> InMemoryPatientRepository:
    return InMemoryPatientRepository()


@pytest.fixture
def membership_repo() -> InMemoryOrganizationMembershipRepository:
    return InMemoryOrganizationMembershipRepository()


@pytest.fixture
def assignment_repo() -> InMemoryPatientAssignmentRepository:
    return InMemoryPatientAssignmentRepository()


@pytest.fixture
def policy(
    patient_repo: InMemoryPatientRepository,
    membership_repo: InMemoryOrganizationMembershipRepository,
    assignment_repo: InMemoryPatientAssignmentRepository,
) -> DefaultPatientAccessPolicy:
    return DefaultPatientAccessPolicy(patient_repo, membership_repo, assignment_repo)


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 1),
        gender="female",
    )


async def _seed_membership(
    repo: InMemoryOrganizationMembershipRepository,
    *,
    org_id,
    user_id,
    status=MembershipStatus.ACTIVE,
    role=OrganizationMembershipRole.DOCTOR,
) -> None:
    await repo.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=user_id,
            membership_role=role,
            status=status,
        ),
    )


async def _seed_assignment(
    repo: InMemoryPatientAssignmentRepository,
    *,
    org_id,
    patient_id,
    doctor_id,
    status=AssignmentStatus.ACTIVE,
    is_primary=False,
    ended_at=None,
) -> None:
    await repo.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient_id,
            assignee_user_id=doctor_id,
            is_primary=is_primary,
            status=status,
            ended_at=ended_at,
        ),
    )


@pytest.mark.asyncio
async def test_doctor_same_org_active_assignment_allowed(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    org_id = uuid4()
    owner_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=owner_id, organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=org_id,
        patient_id=patient.id,
        doctor_id=doctor_id,
        is_primary=True,
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is True
    assert decision.reason_code == PatientAccessReasonCode.ALLOWED_ASSIGNMENT
    assert decision.organization_id == org_id


@pytest.mark.asyncio
async def test_doctor_same_org_primary_assignment_allowed(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=org_id,
        patient_id=patient.id,
        doctor_id=doctor_id,
        is_primary=True,
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is True
    assert decision.reason_code == PatientAccessReasonCode.ALLOWED_ASSIGNMENT


@pytest.mark.asyncio
async def test_doctor_same_org_inactive_assignment_denied(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=org_id,
        patient_id=patient.id,
        doctor_id=doctor_id,
        status=AssignmentStatus.INACTIVE,
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_INACTIVE_ASSIGNMENT


@pytest.mark.asyncio
async def test_doctor_same_org_ended_assignment_denied(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=org_id,
        patient_id=patient.id,
        doctor_id=doctor_id,
        ended_at=datetime.now(UTC),
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_INACTIVE_ASSIGNMENT


@pytest.mark.asyncio
async def test_doctor_same_org_unassigned_denied(
    policy, patient_repo, membership_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_UNASSIGNED


@pytest.mark.asyncio
async def test_doctor_cross_org_assignment_denied(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    patient_org = uuid4()
    other_org = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=patient_org)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=other_org, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=other_org,
        patient_id=patient.id,
        doctor_id=doctor_id,
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_CROSS_ORG


@pytest.mark.asyncio
async def test_doctor_legacy_owner_null_organization_allowed(
    policy, patient_repo,
) -> None:
    doctor_id = uuid4()
    patient = _patient(owner_id=doctor_id, organization_id=None)
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is True
    assert decision.reason_code == PatientAccessReasonCode.ALLOWED_LEGACY_OWNER
    assert decision.organization_id is None


@pytest.mark.asyncio
async def test_unrelated_doctor_legacy_patient_denied(
    policy, patient_repo,
) -> None:
    patient = _patient(owner_id=uuid4(), organization_id=None)
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=uuid4(),
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_UNASSIGNED


@pytest.mark.asyncio
async def test_clinic_admin_same_org_allowed(
    policy, patient_repo, membership_repo,
) -> None:
    org_id = uuid4()
    admin_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(
        membership_repo,
        org_id=org_id,
        user_id=admin_id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )

    decision = await policy.resolve_access(
        actor_id=admin_id,
        actor_role=UserRole.CLINIC_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is True
    assert decision.reason_code == PatientAccessReasonCode.ALLOWED_CLINIC_ADMIN


@pytest.mark.asyncio
async def test_clinic_admin_cross_org_denied(
    policy, patient_repo, membership_repo,
) -> None:
    patient_org = uuid4()
    admin_org = uuid4()
    admin_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=patient_org)
    await patient_repo.create(patient)
    await _seed_membership(
        membership_repo,
        org_id=admin_org,
        user_id=admin_id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )

    decision = await policy.resolve_access(
        actor_id=admin_id,
        actor_role=UserRole.CLINIC_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_CROSS_ORG


@pytest.mark.asyncio
async def test_clinic_admin_inactive_membership_denied(
    policy, patient_repo, membership_repo,
) -> None:
    org_id = uuid4()
    admin_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(
        membership_repo,
        org_id=org_id,
        user_id=admin_id,
        status=MembershipStatus.INACTIVE,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )

    decision = await policy.resolve_access(
        actor_id=admin_id,
        actor_role=UserRole.CLINIC_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_INACTIVE_MEMBERSHIP


@pytest.mark.asyncio
async def test_clinic_admin_legacy_null_org_patient_denied(
    policy, patient_repo,
) -> None:
    admin_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=None)
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=admin_id,
        actor_role=UserRole.CLINIC_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_UNASSIGNED


@pytest.mark.asyncio
async def test_patient_role_denied(policy, patient_repo) -> None:
    user_id = uuid4()
    patient = _patient(owner_id=uuid4(), organization_id=uuid4())
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=user_id,
        actor_role=UserRole.PATIENT,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_ROLE


@pytest.mark.asyncio
async def test_inactive_patient_denied_for_read(policy, patient_repo) -> None:
    patient = _patient(owner_id=uuid4(), organization_id=uuid4())
    patient.is_active = False
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=uuid4(),
        actor_role=UserRole.CLINIC_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_NOT_FOUND


@pytest.mark.asyncio
async def test_system_admin_denied(policy, patient_repo) -> None:
    patient = _patient(owner_id=uuid4(), organization_id=uuid4())
    await patient_repo.create(patient)

    decision = await policy.resolve_access(
        actor_id=uuid4(),
        actor_role=UserRole.SYSTEM_ADMIN,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_ROLE


@pytest.mark.asyncio
async def test_doctor_org_scoped_owner_without_assignment_denied(
    policy, patient_repo, membership_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=doctor_id, organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_UNASSIGNED
    assert decision.suggested_http_status == 404


@pytest.mark.asyncio
async def test_doctor_org_scoped_owner_with_active_assignment_allowed(
    policy, patient_repo, membership_repo, assignment_repo,
) -> None:
    org_id = uuid4()
    doctor_id = uuid4()
    patient = _patient(owner_id=doctor_id, organization_id=org_id)
    await patient_repo.create(patient)
    await _seed_membership(membership_repo, org_id=org_id, user_id=doctor_id)
    await _seed_assignment(
        assignment_repo,
        org_id=org_id,
        patient_id=patient.id,
        doctor_id=doctor_id,
    )

    decision = await policy.resolve_access(
        actor_id=doctor_id,
        actor_role=UserRole.DOCTOR,
        patient_id=patient.id,
        action=PatientAccessAction.READ,
    )
    assert decision.allowed is True
    assert decision.reason_code == PatientAccessReasonCode.ALLOWED_ASSIGNMENT
