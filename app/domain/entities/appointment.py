"""Appointment domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class Appointment(BaseEntity):
    """Healthcare appointment linked to a patient and owned by an authenticated user."""

    owner_id: UUID
    patient_id: UUID
    appointment_date: datetime
    appointment_type: str
    status: str = "scheduled"
    notes: str | None = None
