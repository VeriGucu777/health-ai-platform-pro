"""Clinical encounter domain errors (not HTTP-mapped here)."""


class ClinicalEncounterDomainError(Exception):
    """Base error for encounter bounded context invariants."""


class InvalidEncounterTransitionError(ClinicalEncounterDomainError):
    """Illegal encounter status transition."""


class EncounterAlreadyFinalizedError(ClinicalEncounterDomainError):
    """Operation rejected because encounter is finalized."""


class EncounterCancelledError(ClinicalEncounterDomainError):
    """Operation rejected because encounter is cancelled."""


class EncounterImmutableError(ClinicalEncounterDomainError):
    """Mutation rejected for terminal or inactive encounter."""


class InvalidEncounterVersionError(ClinicalEncounterDomainError):
    """Encounter version invariant violated."""


class InvalidEncounterFieldError(ClinicalEncounterDomainError):
    """Scalar field validation failed on encounter aggregate."""


class InvalidEncounterComplaintError(ClinicalEncounterDomainError):
    """Complaint contract validation failed."""


class InvalidEncounterFindingError(ClinicalEncounterDomainError):
    """Finding contract validation failed."""


class InvalidQuestionResponseError(ClinicalEncounterDomainError):
    """Question response contract validation failed."""


class InvalidEncounterFinalSummaryError(ClinicalEncounterDomainError):
    """Final summary contract validation failed."""
