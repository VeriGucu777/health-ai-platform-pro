"""Unit tests for patient create access policy."""

from uuid import uuid4

import pytest

from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.domain.entities.user import UserRole
from app.domain.organization.enums import OrganizationMembershipRole
from app.domain.patient_access.reason_codes import PatientAccessReasonCode
from tests.support.memory_organization_membership_repository import InMemoryOrganizationMembershipRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.unit.test_patient_access_policy import _seed_membership


@pytest.fixture
def membership_repo() -> InMemoryOrganizationMembershipRepository:
    return InMemoryOrganizationMembershipRepository()


@pytest.fixture
def policy(membership_repo: InMemoryOrganizationMembershipRepository) -> DefaultPatientAccessPolicy:
    return DefaultPatientAccessPolicy(
        InMemoryPatientRepository(),
        membership_repo,
        InMemoryPatientAssignmentRepository(),
    )


@pytest.mark.asyncio
async def test_resolve_create_clinic_admin_single_org_allowed(
    policy, membership_repo,
) -> None:
    admin_id = uuid4()
    org_id = uuid4()
    await _seed_membership(
        membership_repo,
        org_id=org_id,
        user_id=admin_id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    decision = await policy.resolve_create_access(
        actor_id=admin_id,
        actor_role=UserRole.CLINIC_ADMIN,
    )
    assert decision.allowed is True
    assert decision.organization_id == org_id


@pytest.mark.asyncio
async def test_resolve_create_doctor_without_membership_denied(policy) -> None:
    decision = await policy.resolve_create_access(
        actor_id=uuid4(),
        actor_role=UserRole.DOCTOR,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_ROLE


@pytest.mark.asyncio
async def test_resolve_create_patient_role_denied(policy) -> None:
    decision = await policy.resolve_create_access(
        actor_id=uuid4(),
        actor_role=UserRole.PATIENT,
    )
    assert decision.allowed is False
    assert decision.reason_code == PatientAccessReasonCode.DENIED_ROLE
