"""Health measurement repository port."""

from abc import abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.interfaces.repository import Repository


class HealthMeasurementRepository(Repository[HealthMeasurement]):
    """Contract for health measurement persistence scoped to an owning user."""

    @abstractmethod
    async def get_by_id_and_owner(
        self,
        health_measurement_id: UUID,
        owner_id: UUID,
    ) -> HealthMeasurement | None:
        """Retrieve a health measurement only when it belongs to the given owner."""

    @abstractmethod
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
        """List health measurements belonging to the given owner."""

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        glucose_context: str | None = None,
    ) -> int:
        """Count health measurements belonging to the given owner."""
