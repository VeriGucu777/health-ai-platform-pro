"""API schemas for clinic_admin organization and assignment management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.organization.enums import AssignmentStatus, OrganizationMembershipRole


class ClinicAdminMembershipResponse(BaseModel):
    membership_id: UUID
    organization_id: UUID
    membership_role: OrganizationMembershipRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationDoctorMemberResponse(BaseModel):
    membership_id: UUID
    user_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationDoctorMemberListResponse(BaseModel):
    items: list[OrganizationDoctorMemberResponse]


class PatientAssignmentCreate(BaseModel):
    assignee_user_id: UUID
    is_primary: bool = False


class PatientAssignmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    assignee_user_id: UUID
    is_primary: bool
    status: AssignmentStatus
    assigned_at: datetime
    ended_at: datetime | None
    assigned_by_user_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class PatientAssignmentListResponse(BaseModel):
    items: list[PatientAssignmentResponse]
