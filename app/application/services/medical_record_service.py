"""Medical record application service."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.medical_record import MedicalRecordDTO, MedicalRecordListDTO
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.core.exceptions import NotFoundError
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.user import UserRole
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


class MedicalRecordService(ClinicalPatientChildService):
    """Medical record CRUD scoped by patient access policy."""

    def __init__(
        self,
        medical_record_repository: MedicalRecordRepository,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
        membership_repository: OrganizationMembershipRepository | None = None,
    ) -> None:
        super().__init__(patient_repository, access_policy, membership_repository)
        self._medical_records = medical_record_repository

    async def create_medical_record(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        record_date: datetime,
        record_type: str,
        title: str,
        description: str | None = None,
        diagnosis: str | None = None,
        treatment: str | None = None,
        medications: str | None = None,
        doctor_name: str | None = None,
        hospital_name: str | None = None,
        notes: str | None = None,
    ) -> tuple[MedicalRecordDTO, UUID | None]:
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.WRITE,
        )
        medical_record = MedicalRecord(
            owner_id=actor_id,
            patient_id=patient_id,
            record_date=record_date,
            record_type=record_type.strip(),
            title=title.strip(),
            description=description.strip() if description else None,
            diagnosis=diagnosis.strip() if diagnosis else None,
            treatment=treatment.strip() if treatment else None,
            medications=medications.strip() if medications else None,
            doctor_name=doctor_name.strip() if doctor_name else None,
            hospital_name=hospital_name.strip() if hospital_name else None,
            notes=notes.strip() if notes else None,
        )
        created = await self._medical_records.create(medical_record)
        return MedicalRecordDTO.from_entity(created), ctx.organization_id

    async def list_medical_records(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        page: int = 1,
        page_size: int = 20,
        patient_id: UUID | None = None,
        record_type: str | None = None,
    ) -> MedicalRecordListDTO:
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
            return MedicalRecordListDTO.build([], total=0, page=page, page_size=page_size)

        records = await self._medical_records.list_by_patient_ids(
            patient_ids,
            offset=offset,
            limit=page_size,
            patient_id=patient_id,
            record_type=record_type,
        )
        total = await self._medical_records.count_by_patient_ids(
            patient_ids,
            patient_id=patient_id,
            record_type=record_type,
        )
        items = [MedicalRecordDTO.from_entity(record) for record in records]
        return MedicalRecordListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_medical_record(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        medical_record_id: UUID,
    ) -> tuple[MedicalRecordDTO, UUID | None]:
        record, ctx = await self._get_child_with_patient_access(
            self._medical_records,
            medical_record_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.READ,
            not_found_message="Medical record not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        return MedicalRecordDTO.from_entity(record), ctx.organization_id

    async def update_medical_record(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        medical_record_id: UUID,
        *,
        record_date: datetime | None = None,
        record_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        diagnosis: str | None = None,
        treatment: str | None = None,
        medications: str | None = None,
        doctor_name: str | None = None,
        hospital_name: str | None = None,
        notes: str | None = None,
    ) -> tuple[MedicalRecordDTO, UUID | None]:
        medical_record, ctx = await self._get_child_with_patient_access(
            self._medical_records,
            medical_record_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.WRITE,
            not_found_message="Medical record not found",
            patient_id_getter=lambda row: row.patient_id,
        )

        if record_date is not None:
            medical_record.record_date = record_date
        if record_type is not None:
            medical_record.record_type = record_type.strip()
        if title is not None:
            medical_record.title = title.strip()
        if description is not None:
            medical_record.description = description.strip() or None
        if diagnosis is not None:
            medical_record.diagnosis = diagnosis.strip() or None
        if treatment is not None:
            medical_record.treatment = treatment.strip() or None
        if medications is not None:
            medical_record.medications = medications.strip() or None
        if doctor_name is not None:
            medical_record.doctor_name = doctor_name.strip() or None
        if hospital_name is not None:
            medical_record.hospital_name = hospital_name.strip() or None
        if notes is not None:
            medical_record.notes = notes.strip() or None

        medical_record.touch()
        updated = await self._medical_records.update(medical_record)
        return MedicalRecordDTO.from_entity(updated), ctx.organization_id

    async def delete_medical_record(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        medical_record_id: UUID,
    ) -> tuple[UUID | None, UUID]:
        medical_record, ctx = await self._get_child_with_patient_access(
            self._medical_records,
            medical_record_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=PatientAccessAction.DELETE,
            not_found_message="Medical record not found",
            patient_id_getter=lambda row: row.patient_id,
        )
        patient_id = medical_record.patient_id
        deleted = await self._medical_records.delete(medical_record.id)
        if not deleted:
            raise NotFoundError("Medical record not found")
        return ctx.organization_id, patient_id
