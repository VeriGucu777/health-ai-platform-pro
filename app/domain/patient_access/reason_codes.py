"""Reason codes for patient access policy outcomes."""

from enum import StrEnum


class PatientAccessReasonCode(StrEnum):
    """Machine-readable reason for allow/deny decisions."""

    ALLOWED_ASSIGNMENT = "allowed_assignment"
    ALLOWED_LEGACY_OWNER = "allowed_legacy_owner"
    ALLOWED_CLINIC_ADMIN = "allowed_clinic_admin"
    DENIED_CROSS_ORG = "denied_cross_org"
    DENIED_UNASSIGNED = "denied_unassigned"
    DENIED_INACTIVE_MEMBERSHIP = "denied_inactive_membership"
    DENIED_INACTIVE_ASSIGNMENT = "denied_inactive_assignment"
    DENIED_ROLE = "denied_role"
    DENIED_NOT_FOUND = "denied_not_found"
