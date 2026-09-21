"""Patient API request/response schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    """Payload for creating a patient."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=32)
    notes: str | None = None
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class PatientUpdate(BaseModel):
    """Payload for partially updating a patient."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=32)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class PatientResponse(BaseModel):
    """Public patient profile."""

    id: UUID
    owner_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    """Paginated patient list."""

    items: list[PatientResponse]
    total: int
    page: int
    page_size: int
    pages: int
