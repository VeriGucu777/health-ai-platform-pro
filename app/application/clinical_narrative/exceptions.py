"""Clinical narrative generation errors."""

from app.core.exceptions import AppException


class ClinicalNarrativeProviderError(AppException):
    """LLM provider failure (network, timeout, invalid payload)."""

    def __init__(self, message: str = "Clinical narrative provider error", **kwargs) -> None:
        super().__init__(message, status_code=502, **kwargs)


class ClinicalNarrativeValidationError(AppException):
    """Structured output or provenance validation failed."""

    def __init__(self, message: str = "Clinical narrative validation failed", **kwargs) -> None:
        super().__init__(message, status_code=422, **kwargs)


class ClinicalNarrativeHallucinationError(ClinicalNarrativeValidationError):
    """Evidence provenance or clinical guard failed."""

    def __init__(self, message: str = "Clinical narrative failed provenance guard", **kwargs) -> None:
        super().__init__(message, **kwargs)
