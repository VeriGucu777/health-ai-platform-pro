"""Organization clinic domain entities."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities.base import BaseEntity
from app.domain.organization.enums import (
    AssignmentStatus,
    MembershipStatus,
    OrganizationMembershipRole,
)


@dataclass(kw_only=True)
class Organization(BaseEntity):
    """Healthcare organization / clinic tenant."""

    name: str
    slug: str | None = None
    is_active: bool = True


@dataclass(kw_only=True)
class OrganizationMembership:
    """Links a platform user to an organization with a clinic role."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID
    user_id: UUID
    membership_role: OrganizationMembershipRole
    status: MembershipStatus = MembershipStatus.ACTIVE
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    left_at: datetime | None = None


@dataclass(kw_only=True)
class PatientAssignment:
    """Assigns a clinician to a patient within an organization."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID
    patient_id: UUID
    assignee_user_id: UUID
    is_primary: bool = False
    status: AssignmentStatus = AssignmentStatus.ACTIVE
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    assigned_by_user_id: UUID | None = None
