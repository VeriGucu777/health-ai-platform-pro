"""Health measurement API request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.application.validators.health_measurement import (
    has_trackable_value,
    validate_blood_pressure_pair,
)


class HealthMeasurementCreate(BaseModel):
    """Payload for creating a health measurement."""

    patient_id: UUID
    measured_at: datetime
    blood_glucose: Decimal | None = Field(default=None, gt=0)
    glucose_context: str | None = Field(default=None, max_length=50)
    systolic_pressure: int | None = Field(default=None, gt=0)
    diastolic_pressure: int | None = Field(default=None, gt=0)
    heart_rate: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(default=None, gt=0)
    insulin_units: Decimal | None = Field(default=None, ge=0)
    meal_context: str | None = Field(default=None, max_length=50)
    exercise_minutes: int | None = Field(default=None, ge=0)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @model_validator(mode="after")
    def validate_measurement_rules(self) -> Self:
        blood_pressure_error = validate_blood_pressure_pair(
            self.systolic_pressure,
            self.diastolic_pressure,
        )
        if blood_pressure_error is not None:
            raise ValueError(blood_pressure_error)

        if not has_trackable_value(
            blood_glucose=self.blood_glucose,
            systolic_pressure=self.systolic_pressure,
            diastolic_pressure=self.diastolic_pressure,
            heart_rate=self.heart_rate,
            weight_kg=self.weight_kg,
            insulin_units=self.insulin_units,
            exercise_minutes=self.exercise_minutes,
        ):
            raise ValueError("At least one trackable measurement value is required")

        return self


class HealthMeasurementUpdate(BaseModel):
    """Payload for partially updating a health measurement."""

    measured_at: datetime | None = None
    blood_glucose: Decimal | None = Field(default=None, gt=0)
    glucose_context: str | None = Field(default=None, max_length=50)
    systolic_pressure: int | None = Field(default=None, gt=0)
    diastolic_pressure: int | None = Field(default=None, gt=0)
    heart_rate: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(default=None, gt=0)
    insulin_units: Decimal | None = Field(default=None, ge=0)
    meal_context: str | None = Field(default=None, max_length=50)
    exercise_minutes: int | None = Field(default=None, ge=0)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class HealthMeasurementResponse(BaseModel):
    """Public health measurement profile."""

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

    model_config = ConfigDict(from_attributes=True)


class HealthMeasurementListResponse(BaseModel):
    """Paginated health measurement list."""

    items: list[HealthMeasurementResponse]
    total: int
    page: int
    page_size: int
    pages: int


HealthMeasurementSortOrder = Literal["asc", "desc"]
