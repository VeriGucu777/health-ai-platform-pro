"""Appointment repository port."""

from abc import abstractmethod
from uuid import UUID

from app.domain.entities.appointment import Appointment
from app.domain.interfaces.repository import Repository


class AppointmentRepository(Repository[Appointment]):
    """Contract for appointment persistence scoped to an owning user."""

    @abstractmethod
    async def get_by_id_and_owner(
        self,
        appointment_id: UUID,
        owner_id: UUID,
    ) -> Appointment | None:
        """Retrieve an appointment only when it belongs to the given owner."""

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
    ) -> list[Appointment]:
        """List appointments belonging to the given owner."""

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
    ) -> int:
        """Count appointments belonging to the given owner."""
