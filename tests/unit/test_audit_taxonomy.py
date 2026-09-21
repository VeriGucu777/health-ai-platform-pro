"""Audit taxonomy enum tests."""

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType


def test_audit_resource_type_values() -> None:
    assert AuditResourceType.PATIENT == "patient"
    assert AuditResourceType.AUTH == "auth"
    assert AuditResourceType.PATIENT_ASSIGNMENT == "patient_assignment"
    assert AuditResourceType.PATIENT_CONSENT == "patient_consent"
    assert AuditResourceType.PATIENT_CLINICAL_SUMMARY == "patient_clinical_summary"
    assert AuditResourceType.CLINICAL_RETRIEVAL == "clinical_retrieval"
    assert AuditResourceType.CLINICAL_NARRATIVE == "clinical_narrative"
    assert len(AuditResourceType) == 10


def test_audit_action_values() -> None:
    assert AuditAction.VIEW == "view"
    assert AuditAction.LOGIN_FAILURE == "login_failure"
    assert AuditAction.DEACTIVATE == "deactivate"
    assert AuditAction.GRANT == "grant"
    assert AuditAction.REVOKE == "revoke"
    assert AuditAction.SEARCH == "search"
    assert AuditAction.GENERATE == "generate"
    assert len(AuditAction) == 17


def test_audit_outcome_values() -> None:
    assert AuditOutcome.SUCCESS == "success"
    assert AuditOutcome.DENIED == "denied"
    assert len(AuditOutcome) == 4
