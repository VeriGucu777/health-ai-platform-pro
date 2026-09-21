"""Appointment API request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    """Payload for creating an appointment."""

    patient_id: UUID
    appointment_date: datetime
    appointment_type: str = Field(min_length=1, max_length=50)
    status: str = Field(default="scheduled", min_length=1, max_length=30)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AppointmentUpdate(BaseModel):
    """Payload for partially updating an appointment."""

    patient_id: UUID | None = None
    appointment_date: datetime | None = None
    appointment_type: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = Field(default=None, min_length=1, max_length=30)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AppointmentResponse(BaseModel):
    """Public appointment profile."""

    id: UUID
    owner_id: UUID
    patient_id: UUID
    appointment_date: datetime
    appointment_type: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentListResponse(BaseModel):
    """Paginated appointment list."""

    items: list[AppointmentResponse]
    total: int
    page: int
    page_size: int
    pages: int
