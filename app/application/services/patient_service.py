"""Patient application service."""

from datetime import date
from uuid import UUID

from app.application.dtos.patient import PatientDTO, PatientListDTO
from app.application.services.base import BaseService
from app.core.exceptions import NotFoundError
from app.domain.entities.patient import Patient
from app.domain.interfaces.patient_repository import PatientRepository


class PatientService(BaseService):
    """Use cases for patient CRUD scoped to the authenticated owner."""

    def __init__(self, patient_repository: PatientRepository) -> None:
        self._patients = patient_repository

    async def create_patient(
        self,
        owner_id: UUID,
        *,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        gender: str,
        phone: str | None = None,
        notes: str | None = None,
        is_active: bool = True,
    ) -> PatientDTO:
        patient = Patient(
            owner_id=owner_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            date_of_birth=date_of_birth,
            gender=gender.strip(),
            phone=phone.strip() if phone else None,
            notes=notes.strip() if notes else None,
            is_active=is_active,
        )
        created = await self._patients.create(patient)
        return PatientDTO.from_entity(created)

    async def list_patients(
        self,
        owner_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PatientListDTO:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        offset = (page - 1) * page_size
        patients = await self._patients.list_by_owner(owner_id, offset=offset, limit=page_size)
        total = await self._patients.count_by_owner(owner_id)
        items = [PatientDTO.from_entity(patient) for patient in patients]
        return PatientListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_patient(self, owner_id: UUID, patient_id: UUID) -> PatientDTO:
        patient = await self._get_owned_patient(owner_id, patient_id)
        return PatientDTO.from_entity(patient)

    async def update_patient(
        self,
        owner_id: UUID,
        patient_id: UUID,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        date_of_birth: date | None = None,
        gender: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        is_active: bool | None = None,
    ) -> PatientDTO:
        patient = await self._get_owned_patient(owner_id, patient_id)

        if first_name is not None:
            patient.first_name = first_name.strip()
        if last_name is not None:
            patient.last_name = last_name.strip()
        if date_of_birth is not None:
            patient.date_of_birth = date_of_birth
        if gender is not None:
            patient.gender = gender.strip()
        if phone is not None:
            patient.phone = phone.strip() or None
        if notes is not None:
            patient.notes = notes.strip() or None
        if is_active is not None:
            patient.is_active = is_active

        patient.touch()
        updated = await self._patients.update(patient)
        return PatientDTO.from_entity(updated)

    async def delete_patient(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._get_owned_patient(owner_id, patient_id)
        deleted = await self._patients.delete(patient.id)
        if not deleted:
            raise NotFoundError("Patient not found")

    async def _get_owned_patient(self, owner_id: UUID, patient_id: UUID) -> Patient:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        return patient
