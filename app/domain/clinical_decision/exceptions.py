"""Typed errors for clinical decision engine boundaries."""

from app.core.exceptions import AppException, ValidationError


class ClinicalDecisionValidationError(ValidationError):
    """Invalid encounter evaluation context or output constraints."""


class UnsupportedSpecialtyError(ValidationError):
    """Specialty key is not registered for decision evaluation."""


class ClinicalDecisionEngineUnavailableError(AppException):
    """Engine cannot produce an evaluation (infrastructure or configuration)."""

    def __init__(self, message: str = "Clinical decision engine unavailable", **kwargs: object) -> None:
        super().__init__(message, status_code=503, **kwargs)
