"""Clinical evidence source types for summary and future retrieval."""

from enum import StrEnum


class ClinicalEvidenceSourceType(StrEnum):
    """Canonical source types for provenance and RAG-ready retrieval."""

    PATIENT = "patient"
    MEDICAL_RECORD = "medical_record"
    HEALTH_MEASUREMENT = "health_measurement"
    APPOINTMENT = "appointment"
    RISK_ASSESSMENT_HISTORY = "risk_assessment_history"
