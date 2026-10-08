"""Clinical encounter persistence errors (infrastructure layer)."""


class ClinicalEncounterPersistenceError(Exception):
    """Base persistence error for clinical encounter aggregate."""


class ClinicalEncounterConcurrencyError(ClinicalEncounterPersistenceError):
    """Optimistic version conflict on save."""


class ClinicalEncounterMappingError(ClinicalEncounterPersistenceError):
    """ORM/domain mapping failed (invalid persisted shape)."""


class ClinicalEncounterConflictError(ClinicalEncounterPersistenceError):
    """Database uniqueness constraint violated (active encounter, appointment, etc.)."""


class ClinicalEncounterFinalSummaryConflictError(ClinicalEncounterPersistenceError):
    """Attempt to replace an existing final summary."""
