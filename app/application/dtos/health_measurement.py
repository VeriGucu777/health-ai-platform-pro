"""Health measurement-related application DTOs."""

from datetime import datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.health_measurement import HealthMeasurement


class HealthMeasurementDTO(BaseSchema):
    """Health measurement data returned from application services."""

    id: UUID
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
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, health_measurement: HealthMeasurement) -> "HealthMeasurementDTO":
        return cls(
            id=health_measurement.id,
            owner_id=health_measurement.owner_id,
            patient_id=health_measurement.patient_id,
            measured_at=health_measurement.measured_at,
            blood_glucose=health_measurement.blood_glucose,
            glucose_context=health_measurement.glucose_context,
            systolic_pressure=health_measurement.systolic_pressure,
            diastolic_pressure=health_measurement.diastolic_pressure,
            heart_rate=health_measurement.heart_rate,
            weight_kg=health_measurement.weight_kg,
            insulin_units=health_measurement.insulin_units,
            meal_context=health_measurement.meal_context,
            exercise_minutes=health_measurement.exercise_minutes,
            notes=health_measurement.notes,
            created_at=health_measurement.created_at,
            updated_at=health_measurement.updated_at,
        )


class HealthMeasurementListDTO(BaseSchema):
    """Paginated health measurement list."""

    items: list[HealthMeasurementDTO]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[HealthMeasurementDTO],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "HealthMeasurementListDTO":
        pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
