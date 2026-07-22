"""Medical record-related application DTOs."""

from datetime import datetime
from math import ceil
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.medical_record import MedicalRecord


class MedicalRecordDTO(BaseSchema):
    """Medical record data returned from application services."""

    id: UUID
    owner_id: UUID
    patient_id: UUID
    record_date: datetime
    record_type: str
    title: str
    description: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medications: str | None = None
    doctor_name: str | None = None
    hospital_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, medical_record: MedicalRecord) -> "MedicalRecordDTO":
        return cls(
            id=medical_record.id,
            owner_id=medical_record.owner_id,
            patient_id=medical_record.patient_id,
            record_date=medical_record.record_date,
            record_type=medical_record.record_type,
            title=medical_record.title,
            description=medical_record.description,
            diagnosis=medical_record.diagnosis,
            treatment=medical_record.treatment,
            medications=medical_record.medications,
            doctor_name=medical_record.doctor_name,
            hospital_name=medical_record.hospital_name,
            notes=medical_record.notes,
            created_at=medical_record.created_at,
            updated_at=medical_record.updated_at,
        )


class MedicalRecordListDTO(BaseSchema):
    """Paginated medical record list."""

    items: list[MedicalRecordDTO]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[MedicalRecordDTO],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "MedicalRecordListDTO":
        pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
