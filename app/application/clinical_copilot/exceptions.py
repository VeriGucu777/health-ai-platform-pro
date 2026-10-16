"""Clinical Copilot evaluation application errors (no HTTP mapping here)."""

from app.core.exceptions import ConflictError, ValidationError


class ClinicalCopilotEvaluationUnavailableError(ConflictError):
    """Encounter state does not allow Clinical Copilot evaluation."""

    def __init__(
        self,
        message: str = "Clinical Copilot evaluation is not available for this encounter",
    ) -> None:
        super().__init__(message)


class ClinicalCopilotContextProfileError(ValidationError):
    """Invalid or unsupported context profile for the pilot scaffold."""

    def __init__(self, message: str = "Invalid context profile") -> None:
        super().__init__(message)
