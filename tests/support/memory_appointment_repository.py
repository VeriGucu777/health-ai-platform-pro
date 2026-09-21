"""In-memory appointment repository for API tests without a live database."""

from uuid import UUID

from app.domain.entities.appointment import Appointment
from app.domain.interfaces.appointment_repository import AppointmentRepository


class InMemoryAppointmentRepository(AppointmentRepository):
    """Thread-unsafe in-memory store — one instance per test via fixtures."""

    def __init__(self) -> None:
        self._appointments: dict[UUID, Appointment] = {}

    async def get_by_id(self, entity_id: UUID) -> Appointment | None:
        return self._appointments.get(entity_id)

    async def get_by_id_and_owner(
        self,
        appointment_id: UUID,
        owner_id: UUID,
    ) -> Appointment | None:
        appointment = self._appointments.get(appointment_id)
        if appointment is None or appointment.owner_id != owner_id:
            return None
        return appointment

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
    ) -> list[Appointment]:
        owned = [
            appointment
            for appointment in self._appointments.values()
            if appointment.owner_id == owner_id
            and (patient_id is None or appointment.patient_id == patient_id)
        ]
        owned.sort(key=lambda appointment: appointment.created_at, reverse=True)
        return owned[offset : offset + limit]

    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID | None = None,
    ) -> int:
        return sum(
            1
            for appointment in self._appointments.values()
            if appointment.owner_id == owner_id
            and (patient_id is None or appointment.patient_id == patient_id)
        )

    async def list_by_patient_ids(
        self,
        patient_ids: list[UUID],
        *,
        offset: int = 0,
        limit: int = 100,
        patient_id: UUID | None = None,
    ) -> list[Appointment]:
        if not patient_ids:
            return []
        allowed = set(patient_ids)
        if patient_id is not None:
            if patient_id not in allowed:
                return []
            allowed = {patient_id}
        items = [
            appointment
            for appointment in self._appointments.values()
            if appointment.patient_id in allowed
        ]
        items.sort(key=lambda appointment: appointment.created_at, reverse=True)
        return items[offset : offset + limit]

    async def count_by_patient_ids(
        self,
        patient_ids: list[UUID],
        *,
        patient_id: UUID | None = None,
    ) -> int:
        if not patient_ids:
            return 0
        allowed = set(patient_ids)
        if patient_id is not None:
            if patient_id not in allowed:
                return 0
            allowed = {patient_id}
        return sum(
            1
            for appointment in self._appointments.values()
            if appointment.patient_id in allowed
        )

    async def create(self, entity: Appointment) -> Appointment:
        self._appointments[entity.id] = entity
        return entity

    async def update(self, entity: Appointment) -> Appointment:
        if entity.id not in self._appointments:
            msg = "Appointment not found"
            raise ValueError(msg)
        self._appointments[entity.id] = entity
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        return self._appointments.pop(entity_id, None) is not None

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Appointment]:
        appointments = list(self._appointments.values())
        return appointments[offset : offset + limit]
