"""Audit event taxonomy for PHI and security logging."""

from enum import StrEnum


class AuditResourceType(StrEnum):
    """Resource categories referenced in audit records."""

    PATIENT = "patient"
    PATIENT_CLINICAL_TIMELINE = "patient_clinical_timeline"
    PATIENT_CLINICAL_SUMMARY = "patient_clinical_summary"
    CLINICAL_RETRIEVAL = "clinical_retrieval"
    CLINICAL_NARRATIVE = "clinical_narrative"
    RISK_ASSESSMENT = "risk_assessment"
    HEALTH_REPORT = "health_report"
    PATIENT_ASSIGNMENT = "patient_assignment"
    PATIENT_CONSENT = "patient_consent"
    AUTH = "auth"


class AuditAction(StrEnum):
    """Actions recorded in the audit trail."""

    LIST = "list"
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DEACTIVATE = "deactivate"
    GRANT = "grant"
    REVOKE = "revoke"
    EXECUTE = "execute"
    EXPORT = "export"
    SEARCH = "search"
    GENERATE = "generate"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REFRESH = "token_refresh"


class AuditOutcome(StrEnum):
    """Result of the audited operation."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"
