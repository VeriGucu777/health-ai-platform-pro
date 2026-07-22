"""Medical record application service."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.medical_record import MedicalRecordDTO, MedicalRecordListDTO
from app.application.services.base import BaseService
from app.core.exceptions import NotFoundError
from app.domain.entities.medical_record import MedicalRecord
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.patient_repository import PatientRepository


class MedicalRecordService(BaseService):
    """Use cases for medical record CRUD scoped to the authenticated owner."""

    def __init__(
        self,
        medical_record_repository: MedicalRecordRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._medical_records = medical_record_repository
        self._patients = patient_repository

    async def create_medical_record(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        record_date: datetime,
        record_type: str,
        title: str,
        description: str | None = None,
        diagnosis: str | None = None,
        treatment: str | None = None,
        medications: str | None = None,
        doctor_name: str | None = None,
        hospital_name: str | None = None,
        notes: str | None = None,
    ) -> MedicalRecordDTO:
        await self._validate_patient_ownership(owner_id, patient_id)

        medical_record = MedicalRecord(
            owner_id=owner_id,
            patient_id=patient_id,
            record_date=record_date,
            record_type=record_type.strip(),
            title=title.strip(),
            description=description.strip() if description else None,
            diagnosis=diagnosis.strip() if diagnosis else None,
            treatment=treatment.strip() if treatment else None,
            medications=medications.strip() if medications else None,
            doctor_name=doctor_name.strip() if doctor_name else None,
            hospital_name=hospital_name.strip() if hospital_name else None,
            notes=notes.strip() if notes else None,
        )
        created = await self._medical_records.create(medical_record)
        return MedicalRecordDTO.from_entity(created)

    async def list_medical_records(
        self,
        owner_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> MedicalRecordListDTO:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        if patient_id is not None:
            await self._validate_patient_ownership(owner_id, patient_id)

        offset = (page - 1) * page_size
        medical_records = await self._medical_records.list_by_owner(
            owner_id,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
            record_type=record_type,
        )
        total = await self._medical_records.count_by_owner(
            owner_id,
            patient_id=patient_id,
            record_type=record_type,
        )
        items = [MedicalRecordDTO.from_entity(record) for record in medical_records]
        return MedicalRecordListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_medical_record(self, owner_id: UUID, medical_record_id: UUID) -> MedicalRecordDTO:
        medical_record = await self._get_owned_medical_record(owner_id, medical_record_id)
        return MedicalRecordDTO.from_entity(medical_record)

    async def update_medical_record(
        self,
        owner_id: UUID,
        medical_record_id: UUID,
        *,
        record_date: datetime | None = None,
        record_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        diagnosis: str | None = None,
        treatment: str | None = None,
        medications: str | None = None,
        doctor_name: str | None = None,
        hospital_name: str | None = None,
        notes: str | None = None,
    ) -> MedicalRecordDTO:
        medical_record = await self._get_owned_medical_record(owner_id, medical_record_id)

        if record_date is not None:
            medical_record.record_date = record_date
        if record_type is not None:
            medical_record.record_type = record_type.strip()
        if title is not None:
            medical_record.title = title.strip()
        if description is not None:
            medical_record.description = description.strip() or None
        if diagnosis is not None:
            medical_record.diagnosis = diagnosis.strip() or None
        if treatment is not None:
            medical_record.treatment = treatment.strip() or None
        if medications is not None:
            medical_record.medications = medications.strip() or None
        if doctor_name is not None:
            medical_record.doctor_name = doctor_name.strip() or None
        if hospital_name is not None:
            medical_record.hospital_name = hospital_name.strip() or None
        if notes is not None:
            medical_record.notes = notes.strip() or None

        medical_record.touch()
        updated = await self._medical_records.update(medical_record)
        return MedicalRecordDTO.from_entity(updated)

    async def delete_medical_record(self, owner_id: UUID, medical_record_id: UUID) -> None:
        medical_record = await self._get_owned_medical_record(owner_id, medical_record_id)
        deleted = await self._medical_records.delete(medical_record.id)
        if not deleted:
            raise NotFoundError("Medical record not found")

    async def _get_owned_medical_record(
        self,
        owner_id: UUID,
        medical_record_id: UUID,
    ) -> MedicalRecord:
        medical_record = await self._medical_records.get_by_id_and_owner(
            medical_record_id,
            owner_id,
        )
        if medical_record is None:
            raise NotFoundError("Medical record not found")
        return medical_record

    async def _validate_patient_ownership(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")
