"""Medical record API request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MedicalRecordCreate(BaseModel):
    """Payload for creating a medical record."""

    patient_id: UUID
    record_date: datetime
    record_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medications: str | None = None
    doctor_name: str | None = Field(default=None, max_length=100)
    hospital_name: str | None = Field(default=None, max_length=200)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class MedicalRecordUpdate(BaseModel):
    """Payload for partially updating a medical record."""

    record_date: datetime | None = None
    record_type: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medications: str | None = None
    doctor_name: str | None = Field(default=None, max_length=100)
    hospital_name: str | None = Field(default=None, max_length=200)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class MedicalRecordResponse(BaseModel):
    """Public medical record profile."""

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

    model_config = ConfigDict(from_attributes=True)


class MedicalRecordListResponse(BaseModel):
    """Paginated medical record list."""

    items: list[MedicalRecordResponse]
    total: int
    page: int
    page_size: int
    pages: int
