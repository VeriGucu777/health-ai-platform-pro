"""Application errors for clinical decision assembly (no HTTP mapping)."""


class EncounterEvaluationContextAssemblyError(Exception):
    """Base error when encounter context cannot be assembled safely."""


class UnknownClinicalVocabularyKeyError(EncounterEvaluationContextAssemblyError):
    """Structured key is not present in the supplied vocabulary registry view."""


class UnsupportedVitalMappingError(EncounterEvaluationContextAssemblyError):
    """Health measurement field cannot be mapped to a vital observation."""


class EncounterContextAssemblyValidationError(EncounterEvaluationContextAssemblyError):
    """Encounter aggregate state is invalid for structured assembly."""
