"""In-memory health measurement repository for API tests without a live database."""

from datetime import datetime
from uuid import UUID

from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository


class InMemoryHealthMeasurementRepository(HealthMeasurementRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(self) -> None:
        self._health_measurements: dict[UUID, HealthMeasurement] = {}

    async def get_by_id(self, entity_id: UUID) -> HealthMeasurement | None:
        return self._health_measurements.get(entity_id)

    async def get_by_id_and_owner(
        self,
        health_measurement_id: UUID,
        owner_id: UUID,
    ) -> HealthMeasurement | None:
        measurement = self._health_measurements.get(health_measurement_id)
        if measurement is None or measurement.owner_id != owner_id:
            return None
        return measurement

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
        owned = [
            measurement
            for measurement in self._health_measurements.values()
            if measurement.owner_id == owner_id
            and (patient_id is None or measurement.patient_id == patient_id)
            and (date_from is None or measurement.measured_at >= date_from)
            and (date_to is None or measurement.measured_at <= date_to)
            and (glucose_context is None or measurement.glucose_context == glucose_context)
        ]
        owned.sort(
            key=lambda measurement: measurement.measured_at,
            reverse=sort_order == "desc",
        )
        return owned[offset : offset + limit]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        glucose_context: str | None = None,
    ) -> int:
        return sum(
            1
            for measurement in self._health_measurements.values()
            if measurement.owner_id == owner_id
            and (patient_id is None or measurement.patient_id == patient_id)
            and (date_from is None or measurement.measured_at >= date_from)
            and (date_to is None or measurement.measured_at <= date_to)
            and (glucose_context is None or measurement.glucose_context == glucose_context)
        )

    async def list_by_owner_for_analytics(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[HealthMeasurement]:
        owned = [
            measurement
            for measurement in self._health_measurements.values()
            if measurement.owner_id == owner_id
            and measurement.patient_id == patient_id
            and (date_from is None or measurement.measured_at >= date_from)
            and (date_to is None or measurement.measured_at <= date_to)
        ]
        owned.sort(key=lambda measurement: measurement.measured_at)
        return owned

    async def create(self, entity: HealthMeasurement) -> HealthMeasurement:
        self._health_measurements[entity.id] = entity
        return entity

    async def update(self, entity: HealthMeasurement) -> HealthMeasurement:
        if entity.id not in self._health_measurements:
            msg = "Health measurement not found"
            raise ValueError(msg)
        self._health_measurements[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        return self._health_measurements.pop(entity_id, None) is not None

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[HealthMeasurement]:
        measurements = list(self._health_measurements.values())
        return measurements[offset : offset + limit]
