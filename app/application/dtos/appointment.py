"""Appointment-related application DTOs."""

from datetime import datetime
from math import ceil
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.appointment import Appointment


class AppointmentDTO(BaseSchema):
    """Appointment data returned from application services."""

    id: UUID
    owner_id: UUID
    patient_id: UUID
    appointment_date: datetime
    appointment_type: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, appointment: Appointment) -> "AppointmentDTO":
        return cls(
            id=appointment.id,
            owner_id=appointment.owner_id,
            patient_id=appointment.patient_id,
            appointment_date=appointment.appointment_date,
            appointment_type=appointment.appointment_type,
            status=appointment.status,
            notes=appointment.notes,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at,
        )


class AppointmentListDTO(BaseSchema):
    """Paginated appointment list."""

    items: list[AppointmentDTO]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[AppointmentDTO],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "AppointmentListDTO":
        pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
