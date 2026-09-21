"""In-memory patient assignment repository for policy tests."""

from uuid import UUID

from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.organization.entities import PatientAssignment
from app.domain.organization.enums import AssignmentStatus


class InMemoryPatientAssignmentRepository(PatientAssignmentRepository):
    """Stores assignments keyed by (patient_id, assignee_user_id)."""

    def __init__(self) -> None:
        self._assignments: dict[tuple[UUID, UUID], PatientAssignment] = {}

    async def get_by_id(self, entity_id: UUID) -> PatientAssignment | None:
        for assignment in self._assignments.values():
            if assignment.id == entity_id:
                return assignment
        return None

    async def get_by_patient_and_assignee(
        self,
        patient_id: UUID,
        assignee_user_id: UUID,
    ) -> PatientAssignment | None:
        return self._assignments.get((patient_id, assignee_user_id))

    async def list_by_patient_and_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> list[PatientAssignment]:
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.patient_id == patient_id
            and assignment.organization_id == organization_id
        ]

    async def get_active_primary_for_patient_in_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> PatientAssignment | None:
        for assignment in self._assignments.values():
            if (
                assignment.patient_id == patient_id
                and assignment.organization_id == organization_id
                and assignment.status == AssignmentStatus.ACTIVE
                and assignment.is_primary
            ):
                return assignment
        return None

    async def create(self, entity: PatientAssignment) -> PatientAssignment:
        self._assignments[(entity.patient_id, entity.assignee_user_id)] = entity
        return entity

    async def update(self, entity: PatientAssignment) -> PatientAssignment:
        self._assignments[(entity.patient_id, entity.assignee_user_id)] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        for key, assignment in list(self._assignments.items()):
            if assignment.id == entity_id:
                del self._assignments[key]
                return True
        return False
