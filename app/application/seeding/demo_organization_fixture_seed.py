"""Idempotent demo org fixtures: doctor membership, patient, assignment (ops seed only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.application.seeding.demo_clinic_admin_seed import (
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_SLUG,
)
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.user_repository import UserRepository
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.repositories.user_repository import normalize_email


DEMO_DOCTOR_EMAIL = "doctor.demo1@gmail.com"
DEMO_PATIENT_SEED_MARKER = "seed:demo-live-policy-patient-v1"
DEMO_PATIENT_FIRST_NAME = "Demo"
DEMO_PATIENT_LAST_NAME = "Policy Patient"
DEMO_PATIENT_DATE_OF_BIRTH = date(1990, 6, 12)
DEMO_PATIENT_GENDER = "female"


class OrganizationSeedRepository(Protocol):
    async def get_by_slug(self, slug: str): ...


@dataclass(frozen=True)
class DemoOrganizationFixtureSeedConfig:
    organization_slug: str = DEMO_ORGANIZATION_SLUG
    clinic_admin_email: str = DEMO_CLINIC_ADMIN_EMAIL
    demo_doctor_email: str = DEMO_DOCTOR_EMAIL
    patient_first_name: str = DEMO_PATIENT_FIRST_NAME
    patient_last_name: str = DEMO_PATIENT_LAST_NAME
    patient_date_of_birth: date = DEMO_PATIENT_DATE_OF_BIRTH
    patient_gender: str = DEMO_PATIENT_GENDER
    patient_seed_marker: str = DEMO_PATIENT_SEED_MARKER


@dataclass(frozen=True)
class DemoOrganizationFixtureSeedResult:
    organization_id: UUID
    clinic_admin_user_id: UUID
    doctor_user_id: UUID
    patient_id: UUID
    created_doctor_membership: bool
    created_patient: bool
    created_assignment: bool


def _find_demo_patient_in_org(
    patients: list[Patient],
    *,
    marker: str,
    first_name: str,
    last_name: str,
    date_of_birth: date,
) -> Patient | None:
    for patient in patients:
        if patient.notes and marker in patient.notes:
            return patient
    for patient in patients:
        if (
            patient.first_name == first_name
            and patient.last_name == last_name
            and patient.date_of_birth == date_of_birth
        ):
            return patient
    return None


async def seed_demo_organization_fixtures(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: OrganizationMembershipRepository,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
    config: DemoOrganizationFixtureSeedConfig | None = None,
) -> DemoOrganizationFixtureSeedResult:
    """Link demo doctor, patient, and assignment to the demo-live-policy-clinic organization."""
    cfg = config or DemoOrganizationFixtureSeedConfig()

    organization = await organization_repository.get_by_slug(cfg.organization_slug)
    if organization is None:
        msg = (
            f"Organization slug {cfg.organization_slug!r} not found. "
            "Run scripts/seed_demo_clinic_admin.py first."
        )
        raise ValueError(msg)

    clinic_admin = await user_repository.get_by_email(normalize_email(cfg.clinic_admin_email))
    if clinic_admin is None:
        msg = f"Clinic admin user {cfg.clinic_admin_email!r} not found."
        raise ValueError(msg)
    if clinic_admin.role != UserRole.CLINIC_ADMIN:
        msg = f"User {cfg.clinic_admin_email!r} is not clinic_admin."
        raise ValueError(msg)

    doctor = await user_repository.get_by_email(normalize_email(cfg.demo_doctor_email))
    if doctor is None:
        msg = f"Demo doctor user {cfg.demo_doctor_email!r} not found — register the doctor first."
        raise ValueError(msg)
    if doctor.role != UserRole.DOCTOR:
        msg = f"User {cfg.demo_doctor_email!r} must have role doctor."
        raise ValueError(msg)

    created_doctor_membership = False
    doctor_membership = await membership_repository.get_by_organization_and_user(
        organization.id,
        doctor.id,
    )
    if doctor_membership is None:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=doctor.id,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )
        created_doctor_membership = True
    elif (
        doctor_membership.membership_role != OrganizationMembershipRole.DOCTOR
        or doctor_membership.status != MembershipStatus.ACTIVE
    ):
        msg = (
            "Demo doctor has an organization membership that is not an active doctor role; "
            "fix manually before re-running seed"
        )
        raise ValueError(msg)

    org_patients = await patient_repository.list_by_organization_ids(
        [organization.id],
        offset=0,
        limit=500,
    )
    patient = _find_demo_patient_in_org(
        org_patients,
        marker=cfg.patient_seed_marker,
        first_name=cfg.patient_first_name.strip(),
        last_name=cfg.patient_last_name.strip(),
        date_of_birth=cfg.patient_date_of_birth,
    )
    created_patient = False
    if patient is None:
        patient = await patient_repository.create(
            Patient(
                owner_id=clinic_admin.id,
                organization_id=organization.id,
                first_name=cfg.patient_first_name.strip(),
                last_name=cfg.patient_last_name.strip(),
                date_of_birth=cfg.patient_date_of_birth,
                gender=cfg.patient_gender.strip(),
                notes=cfg.patient_seed_marker,
                is_active=True,
            ),
        )
        created_patient = True

    created_assignment = False
    assignment = await assignment_repository.get_by_patient_and_assignee(patient.id, doctor.id)
    if assignment is None:
        await assignment_repository.create(
            PatientAssignment(
                organization_id=organization.id,
                patient_id=patient.id,
                assignee_user_id=doctor.id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
                assigned_by_user_id=clinic_admin.id,
            ),
        )
        created_assignment = True
    elif assignment.status == AssignmentStatus.ACTIVE:
        if assignment.organization_id != organization.id:
            msg = "Demo patient assignment exists in a different organization"
            raise ValueError(msg)
    elif assignment.status == AssignmentStatus.INACTIVE:
        assignment.status = AssignmentStatus.ACTIVE
        assignment.is_primary = True
        assignment.organization_id = organization.id
        assignment.assigned_by_user_id = clinic_admin.id
        await assignment_repository.update(assignment)
    else:
        msg = "Unexpected assignment status for demo doctor/patient pair"
        raise ValueError(msg)

    return DemoOrganizationFixtureSeedResult(
        organization_id=organization.id,
        clinic_admin_user_id=clinic_admin.id,
        doctor_user_id=doctor.id,
        patient_id=patient.id,
        created_doctor_membership=created_doctor_membership,
        created_patient=created_patient,
        created_assignment=created_assignment,
    )
