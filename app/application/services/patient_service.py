"""Patient application service."""

from datetime import date
from uuid import UUID

from app.application.dtos.patient import PatientDTO, PatientListDTO
from app.application.services.base import BaseService
from app.application.services.patient_access_errors import raise_for_patient_access_decision
from app.core.exceptions import NotFoundError
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.organization.entities import PatientAssignment
from app.domain.organization.enums import AssignmentStatus


class PatientService(BaseService):
    """Use cases for patient CRUD scoped to the authenticated owner."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
        membership_repository: OrganizationMembershipRepository | None = None,
        assignment_repository: PatientAssignmentRepository | None = None,
    ) -> None:
        self._patients = patient_repository
        self._access_policy = access_policy
        self._memberships = membership_repository
        self._assignments = assignment_repository

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

    async def create_patient_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        gender: str,
        phone: str | None = None,
        notes: str | None = None,
        is_active: bool = True,
    ) -> tuple[PatientDTO, UUID | None]:
        if self._access_policy is None:
            patient = await self.create_patient(
                actor_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                phone=phone,
                notes=notes,
                is_active=is_active,
            )
            return patient, None

        decision = await self._access_policy.resolve_create_access(
            actor_id=actor_id,
            actor_role=actor_role,
        )
        raise_for_patient_access_decision(decision)
        organization_id = decision.organization_id
        if organization_id is None:
            raise NotFoundError("Patient not found")

        patient = Patient(
            owner_id=actor_id,
            organization_id=organization_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            date_of_birth=date_of_birth,
            gender=gender.strip(),
            phone=phone.strip() if phone else None,
            notes=notes.strip() if notes else None,
            is_active=is_active,
        )
        created = await self._patients.create(patient)

        if actor_role == UserRole.DOCTOR and self._assignments is not None:
            await self._assignments.create(
                PatientAssignment(
                    organization_id=organization_id,
                    patient_id=created.id,
                    assignee_user_id=actor_id,
                    is_primary=True,
                    status=AssignmentStatus.ACTIVE,
                    assigned_by_user_id=actor_id,
                ),
            )

        return PatientDTO.from_entity(created), organization_id

    async def list_patients_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PatientListDTO:
        """List patients visible to the actor under organization/assignment rules."""
        page, page_size, offset = self._normalize_pagination(page, page_size)

        if actor_role == UserRole.DOCTOR:
            patients = await self._patients.list_visible_to_doctor(
                actor_id,
                offset=offset,
                limit=page_size,
            )
            total = await self._patients.count_visible_to_doctor(actor_id)
        elif actor_role == UserRole.CLINIC_ADMIN:
            if self._memberships is None:
                patients = []
                total = 0
            else:
                org_ids = await self._memberships.list_active_organization_ids_for_user(actor_id)
                if not org_ids:
                    patients = []
                    total = 0
                else:
                    patients = await self._patients.list_by_organization_ids(
                        org_ids,
                        offset=offset,
                        limit=page_size,
                    )
                    total = await self._patients.count_by_organization_ids(org_ids)
        else:
            patients = []
            total = 0

        items = [PatientDTO.from_entity(patient) for patient in patients]
        return PatientListDTO.build(items, total=total, page=page, page_size=page_size)

    async def get_patient_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
    ) -> PatientDTO:
        """Retrieve a patient when policy allows access for the actor."""
        if self._access_policy is None:
            return await self.get_patient(actor_id, patient_id)

        decision = await self._access_policy.resolve_access(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            action=PatientAccessAction.READ,
        )
        raise_for_patient_access_decision(decision)

        patient = await self._patients.get_by_id(patient_id)
        if patient is None or not patient.is_active:
            raise NotFoundError("Patient not found")
        return PatientDTO.from_entity(patient)

    async def get_patient_for_user_with_context(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
    ) -> tuple[PatientDTO, UUID | None]:
        """Like get_patient_for_user, also returning policy organization_id for audit."""
        if self._access_policy is None:
            patient_dto = await self.get_patient(actor_id, patient_id)
            return patient_dto, None

        decision = await self._access_policy.resolve_access(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            action=PatientAccessAction.READ,
        )
        raise_for_patient_access_decision(decision)

        patient = await self._patients.get_by_id(patient_id)
        if patient is None or not patient.is_active:
            raise NotFoundError("Patient not found")
        return PatientDTO.from_entity(patient), decision.organization_id

    async def list_patients(
        self,
        owner_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PatientListDTO:
        page, page_size, offset = self._normalize_pagination(page, page_size)
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

    async def update_patient_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        date_of_birth: date | None = None,
        gender: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
    ) -> tuple[PatientDTO, UUID | None]:
        if self._access_policy is None:
            patient = await self.update_patient(
                actor_id,
                patient_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                phone=phone,
                notes=notes,
            )
            return patient, None

        decision = await self._access_policy.resolve_access(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            action=PatientAccessAction.WRITE,
        )
        raise_for_patient_access_decision(decision)

        patient = await self._patients.get_by_id(patient_id)
        if patient is None or not patient.is_active:
            raise NotFoundError("Patient not found")

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

        patient.touch()
        updated = await self._patients.update(patient)
        return PatientDTO.from_entity(updated), decision.organization_id

    async def delete_patient(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._get_owned_patient(owner_id, patient_id)
        await self._deactivate_patient(patient)

    async def delete_patient_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
    ) -> UUID | None:
        if self._access_policy is None:
            await self.delete_patient(actor_id, patient_id)
            return None

        decision = await self._access_policy.resolve_access(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            action=PatientAccessAction.DELETE,
        )
        raise_for_patient_access_decision(decision)

        patient = await self._patients.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Patient not found")

        await self._deactivate_patient(patient)
        return decision.organization_id

    async def _deactivate_patient(self, patient: Patient) -> None:
        if not patient.is_active:
            raise NotFoundError("Patient not found")
        patient.is_active = False
        patient.touch()
        await self._patients.update(patient)

    async def _get_owned_patient(self, owner_id: UUID, patient_id: UUID) -> Patient:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        return patient

    @staticmethod
    def _normalize_pagination(page: int, page_size: int) -> tuple[int, int, int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        offset = (page - 1) * page_size
        return page, page_size, offset
