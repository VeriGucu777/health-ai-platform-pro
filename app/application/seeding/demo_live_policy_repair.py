"""Idempotent repair for demo-live-policy-clinic assignment fixtures (ops only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.application.seeding.demo_clinic_admin_seed import (
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_SLUG,
)
from app.application.seeding.demo_organization_fixture_seed import (
    DEMO_DOCTOR_EMAIL,
    DEMO_PATIENT_DATE_OF_BIRTH,
    DEMO_PATIENT_FIRST_NAME,
    DEMO_PATIENT_LAST_NAME,
    DEMO_PATIENT_SEED_MARKER,
    _find_demo_patient_in_org,
)
from app.application.seeding.demo_unassigned_patient_fixture_seed import (
    DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
    DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
    DEMO_UNASSIGNED_PATIENT_LAST_NAME,
    DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
)
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.user_repository import UserRepository
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.repositories.user_repository import normalize_email


@dataclass(frozen=True)
class DemoAssignmentSnapshot:
    patient_label: str
    patient_id: UUID
    assignment_id: UUID | None
    status: str | None
    assignee_user_id: UUID | None


@dataclass(frozen=True)
class DemoLivePolicyRepairResult:
    organization_id: UUID
    doctor_user_id: UUID
    policy_patient_id: UUID
    unassigned_patient_id: UUID
    policy_assignment_reactivated: bool
    unassigned_assignments_deactivated: int


class OrganizationSeedRepository(Protocol):
    async def get_by_slug(self, slug: str): ...


class MembershipSeedRepository(Protocol):
    async def get_by_organization_and_user(self, organization_id: UUID, user_id: UUID): ...


async def _require_demo_context(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: MembershipSeedRepository,
    organization_slug: str = DEMO_ORGANIZATION_SLUG,
) -> tuple[UUID, UUID, UUID]:
    organization = await organization_repository.get_by_slug(organization_slug)
    if organization is None:
        msg = f"Organization slug {organization_slug!r} not found."
        raise ValueError(msg)

    clinic_admin = await user_repository.get_by_email(normalize_email(DEMO_CLINIC_ADMIN_EMAIL))
    if clinic_admin is None or clinic_admin.role != UserRole.CLINIC_ADMIN:
        msg = "Demo clinic admin account is missing or has wrong role."
        raise ValueError(msg)

    doctor = await user_repository.get_by_email(normalize_email(DEMO_DOCTOR_EMAIL))
    if doctor is None or doctor.role != UserRole.DOCTOR:
        msg = "Demo doctor account is missing or has wrong role."
        raise ValueError(msg)

    membership = await membership_repository.get_by_organization_and_user(
        organization.id,
        doctor.id,
    )
    if membership is None or membership.status != MembershipStatus.ACTIVE:
        msg = "Demo doctor does not have an active organization membership."
        raise ValueError(msg)
    if membership.membership_role != OrganizationMembershipRole.DOCTOR:
        msg = "Demo doctor membership is not a doctor role."
        raise ValueError(msg)

    return organization.id, doctor.id, clinic_admin.id


async def snapshot_demo_assignments(
    *,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
    organization_id: UUID,
    doctor_user_id: UUID,
) -> tuple[DemoAssignmentSnapshot, DemoAssignmentSnapshot]:
    org_patients = await patient_repository.list_by_organization_ids(
        [organization_id],
        offset=0,
        limit=500,
    )
    policy_patient = _find_demo_patient_in_org(
        org_patients,
        marker=DEMO_PATIENT_SEED_MARKER,
        first_name=DEMO_PATIENT_FIRST_NAME,
        last_name=DEMO_PATIENT_LAST_NAME,
        date_of_birth=DEMO_PATIENT_DATE_OF_BIRTH,
    )
    unassigned_patient = _find_demo_patient_in_org(
        org_patients,
        marker=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
        first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
        last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
        date_of_birth=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
    )
    if policy_patient is None or unassigned_patient is None:
        msg = "Demo policy or unassigned patient fixture not found in organization."
        raise ValueError(msg)

    async def _snap_async(label: str, patient_id: UUID) -> DemoAssignmentSnapshot:
        assignment = await assignment_repository.get_by_patient_and_assignee(
            patient_id,
            doctor_user_id,
        )
        if assignment is None:
            return DemoAssignmentSnapshot(
                patient_label=label,
                patient_id=patient_id,
                assignment_id=None,
                status=None,
                assignee_user_id=None,
            )
        return DemoAssignmentSnapshot(
            patient_label=label,
            patient_id=patient_id,
            assignment_id=assignment.id,
            status=assignment.status.value if hasattr(assignment.status, "value") else str(assignment.status),
            assignee_user_id=assignment.assignee_user_id,
        )

    policy_snap = await _snap_async("Demo Policy Patient", policy_patient.id)
    unassigned_snap = await _snap_async("Demo Unassigned Policy Patient", unassigned_patient.id)
    return policy_snap, unassigned_snap


async def repair_demo_live_policy_assignments(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: MembershipSeedRepository,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
) -> DemoLivePolicyRepairResult:
    """Ensure policy patient is actively assigned and unassigned patient is not."""
    organization_id, doctor_id, clinic_admin_id = await _require_demo_context(
        user_repository=user_repository,
        organization_repository=organization_repository,
        membership_repository=membership_repository,
    )

    org_patients = await patient_repository.list_by_organization_ids(
        [organization_id],
        offset=0,
        limit=500,
    )
    policy_patient = _find_demo_patient_in_org(
        org_patients,
        marker=DEMO_PATIENT_SEED_MARKER,
        first_name=DEMO_PATIENT_FIRST_NAME,
        last_name=DEMO_PATIENT_LAST_NAME,
        date_of_birth=DEMO_PATIENT_DATE_OF_BIRTH,
    )
    unassigned_patient = _find_demo_patient_in_org(
        org_patients,
        marker=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
        first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
        last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
        date_of_birth=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
    )
    if policy_patient is None or unassigned_patient is None:
        msg = "Demo policy or unassigned patient fixture not found in organization."
        raise ValueError(msg)

    policy_reactivated = False
    policy_assignment = await assignment_repository.get_by_patient_and_assignee(
        policy_patient.id,
        doctor_id,
    )
    if policy_assignment is None:
        from app.domain.organization.entities import PatientAssignment

        await assignment_repository.create(
            PatientAssignment(
                organization_id=organization_id,
                patient_id=policy_patient.id,
                assignee_user_id=doctor_id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
                assigned_by_user_id=clinic_admin_id,
            ),
        )
        policy_reactivated = True
    elif policy_assignment.status != AssignmentStatus.ACTIVE:
        policy_assignment.status = AssignmentStatus.ACTIVE
        policy_assignment.is_primary = True
        policy_assignment.organization_id = organization_id
        policy_assignment.assigned_by_user_id = clinic_admin_id
        policy_assignment.ended_at = None
        policy_assignment.assigned_at = datetime.now(UTC)
        await assignment_repository.update(policy_assignment)
        policy_reactivated = True

    deactivated = 0
    for assignment in await assignment_repository.list_by_patient_and_organization(
        unassigned_patient.id,
        organization_id,
    ):
        if assignment.assignee_user_id != doctor_id:
            continue
        if assignment.status != AssignmentStatus.ACTIVE:
            continue
        assignment.status = AssignmentStatus.INACTIVE
        assignment.ended_at = datetime.now(UTC)
        await assignment_repository.update(assignment)
        deactivated += 1

    return DemoLivePolicyRepairResult(
        organization_id=organization_id,
        doctor_user_id=doctor_id,
        policy_patient_id=policy_patient.id,
        unassigned_patient_id=unassigned_patient.id,
        policy_assignment_reactivated=policy_reactivated,
        unassigned_assignments_deactivated=deactivated,
    )
