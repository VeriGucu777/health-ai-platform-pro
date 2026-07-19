"""In-memory patient repository for API tests without a live database."""

from uuid import UUID

from app.domain.entities.patient import Patient
from app.domain.interfaces.patient_repository import PatientRepository


class InMemoryPatientRepository(PatientRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(self) -> None:
        self._patients: dict[UUID, Patient] = {}

    async def get_by_id(self, entity_id: UUID) -> Patient | None:
        return self._patients.get(entity_id)

    async def get_by_id_and_owner(self, patient_id: UUID, owner_id: UUID) -> Patient | None:
        patient = self._patients.get(patient_id)
        if patient is None or patient.owner_id != owner_id:
            return None
        return patient

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        owned = [patient for patient in self._patients.values() if patient.owner_id == owner_id]
        owned.sort(key=lambda patient: patient.created_at, reverse=True)
        return owned[offset : offset + limit]

    async def count_by_owner(self, owner_id: UUID) -> int:
        return sum(1 for patient in self._patients.values() if patient.owner_id == owner_id)

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
        return self._patients.pop(entity_id, None) is not None

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Patient]:
        patients = list(self._patients.values())
        return patients[offset : offset + limit]
