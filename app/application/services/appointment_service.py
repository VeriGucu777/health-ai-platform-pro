"""Appointment application service."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.appointment import AppointmentDTO, AppointmentListDTO
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.core.exceptions import NotFoundError
from app.domain.entities.appointment import Appointment
from app.domain.entities.user import UserRole
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


class AppointmentService(ClinicalPatientChildService):
    """Appointment CRUD scoped by patient access policy."""

    def __init__(
        self,
        appointment_repository: AppointmentRepository,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
        membership_repository: OrganizationMembershipRepository | None = None,
    ) -> None:
        super().__init__(patient_repository, access_policy, membership_repository)
        self._appointments = appointment_repository

    async def create_appointment(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        appointment_date: datetime,
        appointment_type: str,
        status: str = "scheduled",
        notes: str | None = None,
    ) -> tuple[AppointmentDTO, UUID | None]:
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.WRITE,
        )

        appointment = Appointment(
            owner_id=actor_id,
            patient_id=patient_id,
            appointment_date=appointment_date,
            appointment_type=appointment_type.strip(),
            status=status.strip(),
            notes=notes.strip() if notes else None,
        )
        created = await self._appointments.create(appointment)
        return AppointmentDTO.from_entity(created), ctx.organization_id

    async def list_appointments(
        self,
        actor_id: UUID,
        actor_role: UserRole,
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
            return AppointmentListDTO.build([], total=0, page=page, page_size=page_size)

        appointments = await self._appointments.list_by_patient_ids(
            patient_ids,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
        )
        total = await self._appointments.count_by_patient_ids(
            patient_ids,
            patient_id=patient_id,
        )
        items = [AppointmentDTO.from_entity(appointment) for appointment in appointments]
        return AppointmentListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_appointment(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        appointment_id: UUID,
    ) -> tuple[AppointmentDTO, UUID | None]:
        appointment, ctx = await self._get_child_with_patient_access(
            self._appointments,
            appointment_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.READ,
            not_found_message="Appointment not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        return AppointmentDTO.from_entity(appointment), ctx.organization_id

    async def update_appointment(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        appointment_id: UUID,
        *,
        patient_id: UUID | None = None,
        appointment_date: datetime | None = None,
        appointment_type: str | None = None,
        status: str | None = None,
        notes: str | None = None,
    ) -> tuple[AppointmentDTO, UUID | None]:
        appointment, ctx = await self._get_child_with_patient_access(
            self._appointments,
            appointment_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.WRITE,
            not_found_message="Appointment not found",
            patient_id_getter=lambda row: row.patient_id,
        )

        if patient_id is not None and patient_id != appointment.patient_id:
            await self._require_patient_access(
                actor_id,
                actor_role,
                patient_id,
                PatientAccessAction.WRITE,
            )
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
        return AppointmentDTO.from_entity(updated), ctx.organization_id

    async def delete_appointment(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        appointment_id: UUID,
    ) -> tuple[UUID | None, UUID]:
        appointment, ctx = await self._get_child_with_patient_access(
            self._appointments,
            appointment_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.DELETE,
            not_found_message="Appointment not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        patient_id = appointment.patient_id
        deleted = await self._appointments.delete(appointment.id)
        if not deleted:
            raise NotFoundError("Appointment not found")
        return ctx.organization_id, patient_id
