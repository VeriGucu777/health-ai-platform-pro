"""Health measurement application service."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.application.dtos.health_measurement import HealthMeasurementDTO, HealthMeasurementListDTO
from app.application.services.base import BaseService
from app.application.validators.health_measurement import (
    has_trackable_value,
    validate_blood_pressure_pair,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.patient_repository import PatientRepository


class HealthMeasurementService(BaseService):
    """Use cases for health measurement CRUD scoped to the authenticated owner."""

    def __init__(
        self,
        health_measurement_repository: HealthMeasurementRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._health_measurements = health_measurement_repository
        self._patients = patient_repository

    async def create_health_measurement(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        measured_at: datetime,
        blood_glucose: Decimal | None = None,
        glucose_context: str | None = None,
        systolic_pressure: int | None = None,
        diastolic_pressure: int | None = None,
        heart_rate: int | None = None,
        weight_kg: Decimal | None = None,
        insulin_units: Decimal | None = None,
        meal_context: str | None = None,
        exercise_minutes: int | None = None,
        notes: str | None = None,
    ) -> HealthMeasurementDTO:
        await self._validate_patient_ownership(owner_id, patient_id)
        self._validate_measurement_values(
            blood_glucose=blood_glucose,
            systolic_pressure=systolic_pressure,
            diastolic_pressure=diastolic_pressure,
            heart_rate=heart_rate,
            weight_kg=weight_kg,
            insulin_units=insulin_units,
            exercise_minutes=exercise_minutes,
        )

        health_measurement = HealthMeasurement(
            owner_id=owner_id,
            patient_id=patient_id,
            measured_at=measured_at,
            blood_glucose=blood_glucose,
            glucose_context=glucose_context.strip() if glucose_context else None,
            systolic_pressure=systolic_pressure,
            diastolic_pressure=diastolic_pressure,
            heart_rate=heart_rate,
            weight_kg=weight_kg,
            insulin_units=insulin_units,
            meal_context=meal_context.strip() if meal_context else None,
            exercise_minutes=exercise_minutes,
            notes=notes.strip() if notes else None,
        )
        created = await self._health_measurements.create(health_measurement)
        return HealthMeasurementDTO.from_entity(created)

    async def list_health_measurements(
        self,
        owner_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        patient_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        glucose_context: str | None = None,
        sort_order: str = "desc",
    ) -> HealthMeasurementListDTO:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        if patient_id is not None:
            await self._validate_patient_ownership(owner_id, patient_id)

        self._validate_date_range(date_from, date_to)

        if sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order must be 'asc' or 'desc'")

        offset = (page - 1) * page_size
        measurements = await self._health_measurements.list_by_owner(
            owner_id,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            glucose_context=glucose_context,
            sort_order=sort_order,
        )
        total = await self._health_measurements.count_by_owner(
            owner_id,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            glucose_context=glucose_context,
        )
        items = [HealthMeasurementDTO.from_entity(measurement) for measurement in measurements]
        return HealthMeasurementListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_health_measurement(
        self,
        owner_id: UUID,
        health_measurement_id: UUID,
    ) -> HealthMeasurementDTO:
        health_measurement = await self._get_owned_health_measurement(owner_id, health_measurement_id)
        return HealthMeasurementDTO.from_entity(health_measurement)

    async def update_health_measurement(
        self,
        owner_id: UUID,
        health_measurement_id: UUID,
        patch: dict[str, object],
    ) -> HealthMeasurementDTO:
        health_measurement = await self._get_owned_health_measurement(owner_id, health_measurement_id)

        if "measured_at" in patch:
            health_measurement.measured_at = patch["measured_at"]  # type: ignore[assignment]
        if "blood_glucose" in patch:
            health_measurement.blood_glucose = patch["blood_glucose"]  # type: ignore[assignment]
        if "glucose_context" in patch:
            glucose_context = patch["glucose_context"]
            health_measurement.glucose_context = (
                glucose_context.strip() if isinstance(glucose_context, str) and glucose_context else None
            )
        if "systolic_pressure" in patch:
            health_measurement.systolic_pressure = patch["systolic_pressure"]  # type: ignore[assignment]
        if "diastolic_pressure" in patch:
            health_measurement.diastolic_pressure = patch["diastolic_pressure"]  # type: ignore[assignment]
        if "heart_rate" in patch:
            health_measurement.heart_rate = patch["heart_rate"]  # type: ignore[assignment]
        if "weight_kg" in patch:
            health_measurement.weight_kg = patch["weight_kg"]  # type: ignore[assignment]
        if "insulin_units" in patch:
            health_measurement.insulin_units = patch["insulin_units"]  # type: ignore[assignment]
        if "meal_context" in patch:
            meal_context = patch["meal_context"]
            health_measurement.meal_context = (
                meal_context.strip() if isinstance(meal_context, str) and meal_context else None
            )
        if "exercise_minutes" in patch:
            health_measurement.exercise_minutes = patch["exercise_minutes"]  # type: ignore[assignment]
        if "notes" in patch:
            notes = patch["notes"]
            health_measurement.notes = notes.strip() if isinstance(notes, str) and notes else None

        self._validate_measurement_values(
            blood_glucose=health_measurement.blood_glucose,
            systolic_pressure=health_measurement.systolic_pressure,
            diastolic_pressure=health_measurement.diastolic_pressure,
            heart_rate=health_measurement.heart_rate,
            weight_kg=health_measurement.weight_kg,
            insulin_units=health_measurement.insulin_units,
            exercise_minutes=health_measurement.exercise_minutes,
        )

        health_measurement.touch()
        updated = await self._health_measurements.update(health_measurement)
        return HealthMeasurementDTO.from_entity(updated)

    async def delete_health_measurement(self, owner_id: UUID, health_measurement_id: UUID) -> None:
        health_measurement = await self._get_owned_health_measurement(owner_id, health_measurement_id)
        deleted = await self._health_measurements.delete(health_measurement.id)
        if not deleted:
            raise NotFoundError("Health measurement not found")

    async def _get_owned_health_measurement(
        self,
        owner_id: UUID,
        health_measurement_id: UUID,
    ) -> HealthMeasurement:
        health_measurement = await self._health_measurements.get_by_id_and_owner(
            health_measurement_id,
            owner_id,
        )
        if health_measurement is None:
            raise NotFoundError("Health measurement not found")
        return health_measurement

    async def _validate_patient_ownership(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> None:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")

    def _validate_measurement_values(
        self,
        *,
        blood_glucose: Decimal | None,
        systolic_pressure: int | None,
        diastolic_pressure: int | None,
        heart_rate: int | None,
        weight_kg: Decimal | None,
        insulin_units: Decimal | None,
        exercise_minutes: int | None,
    ) -> None:
        blood_pressure_error = validate_blood_pressure_pair(systolic_pressure, diastolic_pressure)
        if blood_pressure_error is not None:
            raise ValidationError(blood_pressure_error)

        if not has_trackable_value(
            blood_glucose=blood_glucose,
            systolic_pressure=systolic_pressure,
            diastolic_pressure=diastolic_pressure,
            heart_rate=heart_rate,
            weight_kg=weight_kg,
            insulin_units=insulin_units,
            exercise_minutes=exercise_minutes,
        ):
            raise ValidationError("At least one trackable measurement value is required")
