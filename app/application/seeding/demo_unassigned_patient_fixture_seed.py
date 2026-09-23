"""Idempotent demo org patient without doctor assignment (RBAC negative-test fixture)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.application.seeding.demo_clinic_admin_seed import (
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_SLUG,
)
from app.application.seeding.demo_organization_fixture_seed import (
    DEMO_PATIENT_SEED_MARKER,
    _find_demo_patient_in_org,
)
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.repositories.user_repository import normalize_email

DEMO_UNASSIGNED_PATIENT_SEED_MARKER = "seed:demo-live-unassigned-patient-v1"
DEMO_UNASSIGNED_PATIENT_FIRST_NAME = "Demo"
DEMO_UNASSIGNED_PATIENT_LAST_NAME = "Unassigned Policy Patient"
DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH = date(1991, 3, 20)
DEMO_UNASSIGNED_PATIENT_GENDER = "male"


class OrganizationSeedRepository(Protocol):
    async def get_by_slug(self, slug: str): ...


@dataclass(frozen=True)
class DemoUnassignedPatientFixtureSeedConfig:
    organization_slug: str = DEMO_ORGANIZATION_SLUG
    clinic_admin_email: str = DEMO_CLINIC_ADMIN_EMAIL
    patient_first_name: str = DEMO_UNASSIGNED_PATIENT_FIRST_NAME
    patient_last_name: str = DEMO_UNASSIGNED_PATIENT_LAST_NAME
    patient_date_of_birth: date = DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH
    patient_gender: str = DEMO_UNASSIGNED_PATIENT_GENDER
    patient_seed_marker: str = DEMO_UNASSIGNED_PATIENT_SEED_MARKER


@dataclass(frozen=True)
class DemoUnassignedPatientFixtureSeedResult:
    organization_id: UUID
    clinic_admin_user_id: UUID
    patient_id: UUID
    created_patient: bool


async def seed_demo_unassigned_patient_fixture(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
    config: DemoUnassignedPatientFixtureSeedConfig | None = None,
) -> DemoUnassignedPatientFixtureSeedResult:
    """Create a synthetic org-scoped patient with no assignment to the demo doctor."""
    cfg = config or DemoUnassignedPatientFixtureSeedConfig()

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

    if patient.notes and DEMO_PATIENT_SEED_MARKER in patient.notes:
        msg = "Unassigned seed marker matched the assigned demo patient; check configuration."
        raise ValueError(msg)

    org_assignments = await assignment_repository.list_by_patient_and_organization(
        patient.id,
        organization.id,
    )
    if org_assignments:
        msg = (
            "Unassigned demo patient already has doctor assignment(s); "
            "remove assignments manually or use a fresh seed marker."
        )
        raise ValueError(msg)

    return DemoUnassignedPatientFixtureSeedResult(
        organization_id=organization.id,
        clinic_admin_user_id=clinic_admin.id,
        patient_id=patient.id,
        created_patient=created_patient,
    )
