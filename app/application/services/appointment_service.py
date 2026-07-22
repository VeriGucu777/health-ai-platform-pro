"""Appointment application service."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.appointment import AppointmentDTO, AppointmentListDTO
from app.application.services.base import BaseService
from app.core.exceptions import NotFoundError
from app.domain.entities.appointment import Appointment
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.patient_repository import PatientRepository


class AppointmentService(BaseService):
    """Use cases for appointment CRUD scoped to the authenticated owner."""

    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._appointments = appointment_repository
        self._patients = patient_repository

    async def create_appointment(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        appointment_date: datetime,
        appointment_type: str,
        status: str = "scheduled",
        notes: str | None = None,
    ) -> AppointmentDTO:
        await self._validate_patient_ownership(owner_id, patient_id)

        appointment = Appointment(
            owner_id=owner_id,
            patient_id=patient_id,
            appointment_date=appointment_date,
            appointment_type=appointment_type.strip(),
            status=status.strip(),
            notes=notes.strip() if notes else None,
        )
        created = await self._appointments.create(appointment)
        return AppointmentDTO.from_entity(created)

    async def list_appointments(
        self,
        owner_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        patient_id: UUID | None = None,
    ) -> AppointmentListDTO:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        if patient_id is not None:
            await self._validate_patient_ownership(owner_id, patient_id)

        offset = (page - 1) * page_size
        appointments = await self._appointments.list_by_owner(
            owner_id,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
        )
        total = await self._appointments.count_by_owner(owner_id, patient_id=patient_id)
        items = [AppointmentDTO.from_entity(appointment) for appointment in appointments]
        return AppointmentListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_appointment(self, owner_id: UUID, appointment_id: UUID) -> AppointmentDTO:
        appointment = await self._get_owned_appointment(owner_id, appointment_id)
        return AppointmentDTO.from_entity(appointment)

    async def update_appointment(
        self,
        owner_id: UUID,
        appointment_id: UUID,
        *,
        patient_id: UUID | None = None,
        appointment_date: datetime | None = None,
        appointment_type: str | None = None,
        status: str | None = None,
        notes: str | None = None,
    ) -> AppointmentDTO:
        appointment = await self._get_owned_appointment(owner_id, appointment_id)

        if patient_id is not None:
            await self._validate_patient_ownership(owner_id, patient_id)
            appointment.patient_id = patient_id
        if appointment_date is not None:
            appointment.appointment_date = appointment_date
        if appointment_type is not None:
            appointment.appointment_type = appointment_type.strip()
        if status is not None:
            appointment.status = status.strip()
        if notes is not None:
            appointment.notes = notes.strip() or None

        appointment.touch()
        updated = await self._appointments.update(appointment)
        return AppointmentDTO.from_entity(updated)

    async def delete_appointment(self, owner_id: UUID, appointment_id: UUID) -> None:
        appointment = await self._get_owned_appointment(owner_id, appointment_id)
        deleted = await self._appointments.delete(appointment.id)
        if not deleted:
            raise NotFoundError("Appointment not found")

    async def _get_owned_appointment(self, owner_id: UUID, appointment_id: UUID) -> Appointment:
        appointment = await self._appointments.get_by_id_and_owner(appointment_id, owner_id)
        if appointment is None:
            raise NotFoundError("Appointment not found")
        return appointment

    async def _validate_patient_ownership(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")
