"""Patient assignment repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.interfaces.repository import Repository
from app.domain.organization.entities import PatientAssignment


class PatientAssignmentRepository(Repository[PatientAssignment]):
    """Contract for doctor–patient assignment persistence."""

    @abstractmethod
    async def get_by_patient_and_assignee(
        self,
        patient_id: UUID,
        assignee_user_id: UUID,
    ) -> PatientAssignment | None:
        """Return the assignment row for the patient/assignee pair, any status."""

    @abstractmethod
    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientAssignment]:
        """Return all assignments for a patient scoped to an organization."""

    @abstractmethod
    async def get_active_primary_for_patient_in_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> PatientAssignment | None:
        """Return the active primary assignment for a patient in an organization, if any."""
