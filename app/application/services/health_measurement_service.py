"""Health measurement application service."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.application.dtos.health_measurement import HealthMeasurementDTO, HealthMeasurementListDTO
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.application.validators.health_measurement import (
    has_trackable_value,
    validate_blood_pressure_pair,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.user import UserRole
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


class HealthMeasurementService(ClinicalPatientChildService):
    """Health measurement CRUD scoped by patient access policy."""

    def __init__(
        self,
        health_measurement_repository: HealthMeasurementRepository,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
        membership_repository: OrganizationMembershipRepository | None = None,
    ) -> None:
        super().__init__(patient_repository, access_policy, membership_repository)
        self._health_measurements = health_measurement_repository

    async def create_health_measurement(
        self,
        actor_id: UUID,
        actor_role: UserRole,
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
    ) -> tuple[HealthMeasurementDTO, UUID | None]:
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.WRITE,
        )
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
            owner_id=actor_id,
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
        return HealthMeasurementDTO.from_entity(created), ctx.organization_id

    async def list_health_measurements(
        self,
        actor_id: UUID,
        actor_role: UserRole,
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
        self._validate_date_range(date_from, date_to)
        if sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order must be 'asc' or 'desc'")

        if patient_id is not None:
            await self._require_patient_access(
                actor_id,
                actor_role,
                patient_id,
                PatientAccessAction.READ,
            )
            patient_ids = [patient_id]
        else:
            patient_ids = await self._accessible_patient_ids(actor_id, actor_role)

        offset = (page - 1) * page_size
        if not patient_ids:
            return HealthMeasurementListDTO.build([], total=0, page=page, page_size=page_size)

        measurements = await self._health_measurements.list_by_patient_ids(
            patient_ids,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            glucose_context=glucose_context,
            sort_order=sort_order,
        )
        total = await self._health_measurements.count_by_patient_ids(
            patient_ids,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            glucose_context=glucose_context,
        )
        items = [HealthMeasurementDTO.from_entity(measurement) for measurement in measurements]
        return HealthMeasurementListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_health_measurement(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        health_measurement_id: UUID,
    ) -> tuple[HealthMeasurementDTO, UUID | None]:
        measurement, ctx = await self._get_child_with_patient_access(
            self._health_measurements,
            health_measurement_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.READ,
            not_found_message="Health measurement not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        return HealthMeasurementDTO.from_entity(measurement), ctx.organization_id

    async def update_health_measurement(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        health_measurement_id: UUID,
        patch: dict[str, object],
    ) -> tuple[HealthMeasurementDTO, UUID | None]:
        if "patient_id" in patch:
            raise ValidationError("patient_id cannot be changed")

        health_measurement, ctx = await self._get_child_with_patient_access(
            self._health_measurements,
            health_measurement_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.WRITE,
            not_found_message="Health measurement not found",
            patient_id_getter=lambda row: row.patient_id,
        )

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
        return HealthMeasurementDTO.from_entity(updated), ctx.organization_id

    async def delete_health_measurement(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        health_measurement_id: UUID,
    ) -> tuple[UUID | None, UUID]:
        health_measurement, ctx = await self._get_child_with_patient_access(
            self._health_measurements,
            health_measurement_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.DELETE,
            not_found_message="Health measurement not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        patient_id = health_measurement.patient_id
        deleted = await self._health_measurements.delete(health_measurement.id)
        if not deleted:
            raise NotFoundError("Health measurement not found")
        return ctx.organization_id, patient_id

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
