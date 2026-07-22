"""Medical record domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class MedicalRecord(BaseEntity):
    """Clinical record linked to a patient and owned by an authenticated user."""

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
