"""Build ClinicalEncounterService with in-memory policy dependencies."""

from __future__ import annotations

from app.application.services.clinical_encounter_service import ClinicalEncounterService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.core.config import Settings
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from tests.support.memory_clinical_encounter_repository import InMemoryClinicalEncounterRepository
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository


def build_clinical_encounter_service(
    *,
    encounter_repository: InMemoryClinicalEncounterRepository | None = None,
    patient_repository: InMemoryPatientRepository | None = None,
    membership_repository: InMemoryOrganizationMembershipRepository | None = None,
    assignment_repository: InMemoryPatientAssignmentRepository | None = None,
    settings: Settings | None = None,
    consent_repository: PatientConsentRepository | None = None,
    transaction=None,
) -> ClinicalEncounterService:
    assignments = assignment_repository or InMemoryPatientAssignmentRepository()
    memberships = membership_repository or InMemoryOrganizationMembershipRepository()
    patients = patient_repository or InMemoryPatientRepository(assignment_repository=assignments)
    policy = DefaultPatientAccessPolicy(patients, memberships, assignments)
    return ClinicalEncounterService(
        encounter_repository or InMemoryClinicalEncounterRepository(),
        patients,
        access_policy=policy,
        membership_repository=memberships,
        settings=settings,
        consent_repository=consent_repository,
        transaction=transaction,
    )
