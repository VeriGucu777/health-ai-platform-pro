"""Enumerations for clinical decision engine inputs and outputs."""

from enum import StrEnum


class EvaluationStatus(StrEnum):
    SUCCESS = "success"
    NO_APPLICABLE_RULES = "no_applicable_rules"
    UNAVAILABLE = "unavailable"
    INVALID_CONTEXT = "invalid_context"


class QuestionType(StrEnum):
    HISTORY = "history"
    SYMPTOM = "symptom"
    RISK_FACTOR = "risk_factor"
    MEDICATION_HISTORY = "medication_history"
    FAMILY_HISTORY = "family_history"
    FUNCTIONAL_STATUS = "functional_status"
    OTHER = "other"


class MissingInformationCriticality(StrEnum):
    ROUTINE = "routine"
    IMPORTANT = "important"
    CRITICAL = "critical"


class SafetyAlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class ClinicalInputSource(StrEnum):
    PATIENT_REPORTED = "patient_reported"
    CLINICIAN_OBSERVED = "clinician_observed"
    DEVICE = "device"
    RECORD = "record"


class TriggeredInputType(StrEnum):
    COMPLAINT = "complaint"
    FINDING = "finding"
    VITAL = "vital"
    QUESTION_RESPONSE = "question_response"
    DEMOGRAPHIC = "demographic"
    HISTORICAL = "historical"
