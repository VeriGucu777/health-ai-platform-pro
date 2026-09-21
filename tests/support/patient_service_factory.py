"""Build PatientService wired for policy-based list/get in API tests."""

from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.patient_service import PatientService
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository


def build_policy_patient_service(
    patient_repository: InMemoryPatientRepository,
    membership_repository: InMemoryOrganizationMembershipRepository,
    assignment_repository: InMemoryPatientAssignmentRepository,
) -> PatientService:
    """Return a PatientService with DefaultPatientAccessPolicy for HTTP tests."""
    access_policy = DefaultPatientAccessPolicy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    return PatientService(
        patient_repository,
        access_policy,
        membership_repository,
        assignment_repository,
    )
