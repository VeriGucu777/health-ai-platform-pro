"""Health measurement domain entity."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class HealthMeasurement(BaseEntity):
    """Patient health measurement owned by an authenticated user."""

    owner_id: UUID
    patient_id: UUID
    measured_at: datetime
    blood_glucose: Decimal | None = None
    glucose_context: str | None = None
    systolic_pressure: int | None = None
    diastolic_pressure: int | None = None
    heart_rate: int | None = None
    weight_kg: Decimal | None = None
    insulin_units: Decimal | None = None
    meal_context: str | None = None
    exercise_minutes: int | None = None
    notes: str | None = None
