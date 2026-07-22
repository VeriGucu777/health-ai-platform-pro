"""SQLAlchemy health measurement repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.interfaces.health_measurement_repository import (
    HealthMeasurementRepository as HealthMeasurementRepositoryPort,
)
from app.infrastructure.database.models.health_measurement import HealthMeasurementModel
from app.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyHealthMeasurementRepository(
    SQLAlchemyRepository[HealthMeasurementModel, HealthMeasurement],
    HealthMeasurementRepositoryPort,
):
    """PostgreSQL-backed health measurement repository with owner scoping."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, HealthMeasurementModel)

    async def get_by_id_and_owner(
        self,
        health_measurement_id: UUID,
        owner_id: UUID,
    ) -> HealthMeasurement | None:
        stmt = select(HealthMeasurementModel).where(
            HealthMeasurementModel.id == health_measurement_id,
            HealthMeasurementModel.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        glucose_context: str | None = None,
        sort_order: str = "desc",
    ) -> list[HealthMeasurement]:
        stmt = select(HealthMeasurementModel).where(HealthMeasurementModel.owner_id == owner_id)
        stmt = self._apply_filters(stmt, patient_id, date_from, date_to, glucose_context)
        order_column = HealthMeasurementModel.measured_at
        stmt = stmt.order_by(
            order_column.desc() if sort_order == "desc" else order_column.asc(),
        ).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        glucose_context: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(HealthMeasurementModel)
            .where(HealthMeasurementModel.owner_id == owner_id)
        )
        stmt = self._apply_filters(stmt, patient_id, date_from, date_to, glucose_context)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    def _apply_filters(
        self,
        stmt,
        patient_id: UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        glucose_context: str | None,
    ):
        if patient_id is not None:
            stmt = stmt.where(HealthMeasurementModel.patient_id == patient_id)
        if date_from is not None:
            stmt = stmt.where(HealthMeasurementModel.measured_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(HealthMeasurementModel.measured_at <= date_to)
        if glucose_context is not None:
            stmt = stmt.where(HealthMeasurementModel.glucose_context == glucose_context)
        return stmt

    def _to_entity(self, model: HealthMeasurementModel) -> HealthMeasurement:
        return HealthMeasurement(
            id=model.id,
            owner_id=model.owner_id,
            patient_id=model.patient_id,
            measured_at=model.measured_at,
            blood_glucose=model.blood_glucose,
            glucose_context=model.glucose_context,
            systolic_pressure=model.systolic_pressure,
            diastolic_pressure=model.diastolic_pressure,
            heart_rate=model.heart_rate,
            weight_kg=model.weight_kg,
            insulin_units=model.insulin_units,
            meal_context=model.meal_context,
            exercise_minutes=model.exercise_minutes,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: HealthMeasurement) -> HealthMeasurementModel:
        return HealthMeasurementModel(
            id=entity.id,
            owner_id=entity.owner_id,
            patient_id=entity.patient_id,
            measured_at=entity.measured_at,
            blood_glucose=entity.blood_glucose,
            glucose_context=entity.glucose_context,
            systolic_pressure=entity.systolic_pressure,
            diastolic_pressure=entity.diastolic_pressure,
            heart_rate=entity.heart_rate,
            weight_kg=entity.weight_kg,
            insulin_units=entity.insulin_units,
            meal_context=entity.meal_context,
            exercise_minutes=entity.exercise_minutes,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
