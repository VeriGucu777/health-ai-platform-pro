"""In-memory medical record repository for API tests without a live database."""

from uuid import UUID

from app.domain.entities.medical_record import MedicalRecord
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository


class InMemoryMedicalRecordRepository(MedicalRecordRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(self) -> None:
        self._medical_records: dict[UUID, MedicalRecord] = {}

    async def get_by_id(self, entity_id: UUID) -> MedicalRecord | None:
        return self._medical_records.get(entity_id)

    async def get_by_id_and_owner(
        self,
        medical_record_id: UUID,
        owner_id: UUID,
    ) -> MedicalRecord | None:
        medical_record = self._medical_records.get(medical_record_id)
        if medical_record is None or medical_record.owner_id != owner_id:
            return None
        return medical_record

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> list[MedicalRecord]:
        owned = [
            medical_record
            for medical_record in self._medical_records.values()
            if medical_record.owner_id == owner_id
            and (patient_id is None or medical_record.patient_id == patient_id)
            and (record_type is None or medical_record.record_type == record_type)
        ]
        owned.sort(key=lambda medical_record: medical_record.created_at, reverse=True)
        return owned[offset : offset + limit]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> int:
        return sum(
            1
            for medical_record in self._medical_records.values()
            if medical_record.owner_id == owner_id
            and (patient_id is None or medical_record.patient_id == patient_id)
            and (record_type is None or medical_record.record_type == record_type)
        )

    async def create(self, entity: MedicalRecord) -> MedicalRecord:
        self._medical_records[entity.id] = entity
        return entity

    async def update(self, entity: MedicalRecord) -> MedicalRecord:
        if entity.id not in self._medical_records:
            msg = "Medical record not found"
            raise ValueError(msg)
        self._medical_records[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        return self._medical_records.pop(entity_id, None) is not None

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[MedicalRecord]:
        medical_records = list(self._medical_records.values())
        return medical_records[offset : offset + limit]
