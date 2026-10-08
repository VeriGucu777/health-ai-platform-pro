"""Clinical encounter application-layer errors (no HTTP mapping here)."""

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class ClinicalEncounterNotFoundError(NotFoundError):
    """Encounter missing or not visible to the actor."""

    def __init__(self, message: str = "Clinical encounter not found") -> None:
        super().__init__(message)


class ClinicalEncounterAccessDeniedError(ForbiddenError):
    """Actor role cannot perform clinical encounter mutations."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)


class ClinicalEncounterOwnershipError(ClinicalEncounterNotFoundError):
    """Non-owner mutation attempt — masked as not found."""


class ActiveClinicalEncounterAlreadyExists(ConflictError):
    """Patient/org already has an active encounter session."""

    def __init__(self, message: str = "An active clinical encounter already exists") -> None:
        super().__init__(message)


class ClinicalEncounterStaleVersionError(ConflictError):
    """Optimistic concurrency failure at persistence boundary."""

    def __init__(
        self,
        message: str = "Clinical encounter was updated elsewhere; reload and retry",
    ) -> None:
        super().__init__(message)


class ClinicalEncounterApplicationConflictError(ConflictError):
    """Generic encounter workflow conflict."""

    def __init__(self, message: str = "Clinical encounter conflict") -> None:
        super().__init__(message)


class ClinicalEncounterFinalizationError(ConflictError):
    """Finalize preconditions failed or summary conflict."""

    def __init__(self, message: str = "Clinical encounter finalization failed") -> None:
        super().__init__(message)
