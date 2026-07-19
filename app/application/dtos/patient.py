"""Patient-related application DTOs."""

from datetime import date, datetime
from math import ceil
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.patient import Patient


class PatientDTO(BaseSchema):
    """Patient data returned from application services."""

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

    @classmethod
    def from_entity(cls, patient: Patient) -> "PatientDTO":
        return cls(
            id=patient.id,
            owner_id=patient.owner_id,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            phone=patient.phone,
            notes=patient.notes,
            is_active=patient.is_active,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )


class PatientListDTO(BaseSchema):
    """Paginated patient list."""

    items: list[PatientDTO]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[PatientDTO],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "PatientListDTO":
        pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
