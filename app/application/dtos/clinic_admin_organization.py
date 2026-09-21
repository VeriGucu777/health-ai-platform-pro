"""DTOs for clinic_admin organization and assignment management."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.organization.enums import AssignmentStatus, OrganizationMembershipRole


class ClinicAdminMembershipDTO(BaseSchema):
    """Active clinic_admin membership context for the current user."""

    membership_id: UUID
    organization_id: UUID
    membership_role: OrganizationMembershipRole
    joined_at: datetime


class OrganizationDoctorMemberDTO(BaseSchema):
    """Active doctor member in the clinic_admin's organization (ids only, no PHI)."""

    membership_id: UUID
    user_id: UUID
    joined_at: datetime


class OrganizationDoctorMemberListDTO(BaseSchema):
    items: list[OrganizationDoctorMemberDTO]


class PatientAssignmentDTO(BaseSchema):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    assignee_user_id: UUID
    is_primary: bool
    status: AssignmentStatus
    assigned_at: datetime
    ended_at: datetime | None
    assigned_by_user_id: UUID | None


class PatientAssignmentListDTO(BaseSchema):
    organization_id: UUID
    items: list[PatientAssignmentDTO]
