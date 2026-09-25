"""In-memory patient repository for API tests without a live database."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.entities.patient import Patient
from app.domain.patient.errors import PatientHardDeleteForbiddenError
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.organization.enums import AssignmentStatus

if TYPE_CHECKING:
    from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository


class InMemoryPatientRepository(PatientRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(
        self,
        assignment_repository: InMemoryPatientAssignmentRepository | None = None,
    ) -> None:
        self._patients: dict[UUID, Patient] = {}
        self._assignment_repository = assignment_repository

    async def get_by_id(self, entity_id: UUID) -> Patient | None:
        return self._patients.get(entity_id)

    async def get_by_id_and_owner(self, patient_id: UUID, owner_id: UUID) -> Patient | None:
        patient = self._patients.get(patient_id)
        if patient is None or patient.owner_id != owner_id or not patient.is_active:
            return None
        return patient

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        owned = [
            patient
            for patient in self._patients.values()
            if patient.owner_id == owner_id and patient.is_active
        ]
        owned.sort(key=lambda patient: patient.created_at, reverse=True)
        return owned[offset : offset + limit]

    async def count_by_owner(self, owner_id: UUID) -> int:
        return sum(
            1
            for patient in self._patients.values()
            if patient.owner_id == owner_id and patient.is_active
        )

    async def list_visible_to_doctor(
        self,
        doctor_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        visible = self._visible_patient_ids_for_doctor(doctor_id)
        patients = [
            self._patients[patient_id]
            for patient_id in visible
            if self._patients[patient_id].is_active
        ]
        patients.sort(key=lambda patient: patient.created_at, reverse=True)
        return patients[offset : offset + limit]

    async def count_visible_to_doctor(self, doctor_id: UUID) -> int:
        return len(self._visible_patient_ids_for_doctor(doctor_id))

    async def list_by_organization_ids(
        self,
        organization_ids: list[UUID],
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        org_set = set(organization_ids)
        patients = [
            patient
            for patient in self._patients.values()
            if patient.organization_id in org_set and patient.is_active
        ]
        patients.sort(key=lambda patient: patient.created_at, reverse=True)
        return patients[offset : offset + limit]

    async def count_by_organization_ids(self, organization_ids: list[UUID]) -> int:
        org_set = set(organization_ids)
        return sum(
            1
            for patient in self._patients.values()
            if patient.organization_id in org_set and patient.is_active
        )

    def _visible_patient_ids_for_doctor(self, doctor_id: UUID) -> set[UUID]:
        visible = {
            patient.id
            for patient in self._patients.values()
            if patient.is_active
            and patient.owner_id == doctor_id
            and patient.organization_id is None
        }
        if self._assignment_repository is not None:
            for assignment in self._assignment_repository._assignments.values():
                if assignment.assignee_user_id != doctor_id:
                    continue
                if assignment.status != AssignmentStatus.ACTIVE:
                    continue
                if assignment.ended_at is not None:
                    continue
                patient = self._patients.get(assignment.patient_id)
                if patient is not None and patient.is_active:
                    visible.add(assignment.patient_id)
        return visible

    async def create(self, entity: Patient) -> Patient:
        self._patients[entity.id] = entity
        return entity

    async def update(self, entity: Patient) -> Patient:
        if entity.id not in self._patients:
            msg = "Patient not found"
            raise ValueError(msg)
        self._patients[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        raise PatientHardDeleteForbiddenError(f"Refusing hard delete for patient {entity_id}")

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Patient]:
        patients = list(self._patients.values())
        return patients[offset : offset + limit]
