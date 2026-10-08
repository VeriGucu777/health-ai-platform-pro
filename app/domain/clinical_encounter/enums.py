"""Enumerations for the clinical encounter bounded context."""

from enum import StrEnum


class EncounterStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class FindingType(StrEnum):
    SYMPTOM = "symptom"
    PHYSICAL_EXAM = "physical_exam"
    HISTORY_ITEM = "history_item"
    RISK_FACTOR = "risk_factor"
    NEGATIVE_FINDING = "negative_finding"
    OTHER = "other"


class QuestionAnswerType(StrEnum):
    BOOLEAN = "boolean"
    SINGLE_CHOICE = "single_choice"
    NUMBER = "number"
    TEXT = "text"


class ClinicalInputSource(StrEnum):
    """Provenance for findings; mapped to engine input in application layer."""

    PATIENT_REPORTED = "patient_reported"
    CLINICIAN_OBSERVED = "clinician_observed"
    HISTORICAL_RECORD = "historical_record"
    DEVICE = "device"
    OTHER = "other"


SUPPORTED_ENCOUNTER_LOCALES = frozenset({"tr", "en"})
