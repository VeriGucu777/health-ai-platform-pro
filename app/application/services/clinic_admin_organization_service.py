"""Clinic admin organization membership and patient assignment management."""

from datetime import UTC, datetime
from uuid import UUID

from app.application.dtos.clinic_admin_organization import (
    ClinicAdminMembershipDTO,
    OrganizationDoctorMemberDTO,
    OrganizationDoctorMemberListDTO,
    PatientAssignmentDTO,
    PatientAssignmentListDTO,
)
from app.application.services.base import BaseService
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.organization.entities import PatientAssignment
from app.domain.organization.enums import (
    AssignmentStatus,
    MembershipStatus,
    OrganizationMembershipRole,
)


class ClinicAdminOrganizationService(BaseService):
    """Manage org-scoped doctor memberships and patient assignments for clinic admins."""

    def __init__(
        self,
        membership_repository: OrganizationMembershipRepository,
        assignment_repository: PatientAssignmentRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._memberships = membership_repository
        self._assignments = assignment_repository
        self._patients = patient_repository

    async def get_my_clinic_admin_membership(
        self,
        admin_user_id: UUID,
    ) -> ClinicAdminMembershipDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        membership = await self._memberships.get_by_organization_and_user(
            organization_id,
            admin_user_id,
        )
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise ForbiddenError("Insufficient permissions")
        return ClinicAdminMembershipDTO(
            membership_id=membership.id,
            organization_id=membership.organization_id,
            membership_role=membership.membership_role,
            joined_at=membership.joined_at,
        )

    async def list_organization_doctors(
        self,
        admin_user_id: UUID,
    ) -> OrganizationDoctorMemberListDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        doctor_memberships = await self._memberships.list_active_doctor_memberships_in_organization(
            organization_id,
        )
        items = [
            OrganizationDoctorMemberDTO(
                membership_id=membership.id,
                user_id=membership.user_id,
                joined_at=membership.joined_at,
            )
            for membership in doctor_memberships
        ]
        return OrganizationDoctorMemberListDTO(items=items)

    async def list_patient_assignments(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
    ) -> PatientAssignmentListDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)
        rows = await self._assignments.list_by_patient_and_organization(
            patient_id,
            organization_id,
        )
        return PatientAssignmentListDTO(
            organization_id=organization_id,
            items=[_assignment_dto(row) for row in rows],
        )

    async def create_patient_assignment(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
        *,
        assignee_user_id: UUID,
        is_primary: bool = False,
    ) -> PatientAssignmentDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)
        await self._require_active_doctor_in_organization(assignee_user_id, organization_id)

        existing = await self._assignments.get_by_patient_and_assignee(patient_id, assignee_user_id)
        if existing is not None and existing.status == AssignmentStatus.ACTIVE:
            raise ConflictError("An active assignment already exists for this doctor and patient")
        if existing is not None and existing.organization_id != organization_id:
            raise NotFoundError("Patient not found")

        if is_primary:
            primary = await self._assignments.get_active_primary_for_patient_in_organization(
                patient_id,
                organization_id,
            )
            if primary is not None:
                raise ConflictError("An active primary assignment already exists for this patient")

        if existing is not None and existing.status == AssignmentStatus.INACTIVE:
            existing.status = AssignmentStatus.ACTIVE
            existing.is_primary = is_primary
            existing.ended_at = None
            existing.assigned_by_user_id = admin_user_id
            existing.assigned_at = datetime.now(UTC)
            updated = await self._assignments.update(existing)
            return _assignment_dto(updated)

        assignment = PatientAssignment(
            organization_id=organization_id,
            patient_id=patient_id,
            assignee_user_id=assignee_user_id,
            is_primary=is_primary,
            status=AssignmentStatus.ACTIVE,
            assigned_by_user_id=admin_user_id,
        )
        created = await self._assignments.create(assignment)
        return _assignment_dto(created)

    async def deactivate_patient_assignment(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
        assignment_id: UUID,
    ) -> PatientAssignmentDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)

        assignment = await self._assignments.get_by_id(assignment_id)
        if (
            assignment is None
            or assignment.patient_id != patient_id
            or assignment.organization_id != organization_id
            or assignment.status != AssignmentStatus.ACTIVE
        ):
            raise NotFoundError("Assignment not found")

        assignment.status = AssignmentStatus.INACTIVE
        assignment.ended_at = datetime.now(UTC)
        updated = await self._assignments.update(assignment)
        return _assignment_dto(updated)

    async def _require_single_active_clinic_admin_org(self, admin_user_id: UUID) -> UUID:
        memberships = await self._memberships.list_active_memberships_for_user(
            admin_user_id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
        )
        if not memberships:
            raise ForbiddenError("Insufficient permissions")
        if len(memberships) > 1:
            raise ForbiddenError("Multiple active clinic admin organizations are not supported")
        return memberships[0].organization_id

    async def _require_patient_in_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> None:
        patient = await self._patients.get_by_id(patient_id)
        if (
            patient is None
            or not patient.is_active
            or patient.organization_id != organization_id
        ):
            raise NotFoundError("Patient not found")

    async def _require_active_doctor_in_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        membership = await self._memberships.get_by_organization_and_user(organization_id, user_id)
        if (
            membership is None
            or membership.status != MembershipStatus.ACTIVE
            or membership.membership_role != OrganizationMembershipRole.DOCTOR
        ):
            raise NotFoundError("Doctor not found")


def _assignment_dto(assignment: PatientAssignment) -> PatientAssignmentDTO:
    return PatientAssignmentDTO(
        id=assignment.id,
        organization_id=assignment.organization_id,
        patient_id=assignment.patient_id,
        assignee_user_id=assignment.assignee_user_id,
        is_primary=assignment.is_primary,
        status=assignment.status,
        assigned_at=assignment.assigned_at,
        ended_at=assignment.ended_at,
        assigned_by_user_id=assignment.assigned_by_user_id,
    )
