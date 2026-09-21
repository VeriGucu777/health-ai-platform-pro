"""Enumerations for organization clinic model."""

from enum import StrEnum


class OrganizationMembershipRole(StrEnum):
    """Role of a user within an organization."""

    DOCTOR = "doctor"
    CLINIC_ADMIN = "clinic_admin"


class MembershipStatus(StrEnum):
    """Lifecycle status of an organization membership."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class AssignmentStatus(StrEnum):
    """Lifecycle status of a doctor–patient assignment."""

    ACTIVE = "active"
    INACTIVE = "inactive"
