"""Application-wide exception hierarchy and HTTP mapping."""

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


class UnauthorizedError(AppException):
    """Authentication required or failed."""

    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(message, status_code=401, **kwargs)


class ForbiddenError(AppException):
    """Authenticated but not permitted."""

    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        super().__init__(message, status_code=403, **kwargs)


class ValidationError(AppException):
    """Business rule validation failure."""

    def __init__(self, message: str = "Validation failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=422, **kwargs)


class ConflictError(AppException):
    """Resource conflict (e.g., duplicate email)."""

    def __init__(self, message: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(message, status_code=409, **kwargs)


class ConfigurationError(AppException):
    """Invalid or incomplete deployment configuration."""

    def __init__(self, message: str = "Configuration error", **kwargs: Any) -> None:
        super().__init__(message, status_code=500, **kwargs)


class FeatureDisabledError(AppException):
    """Optional product feature is turned off for this deployment (pilot / capacity)."""

    def __init__(
        self,
        message: str = "This feature is disabled in the current deployment",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=503, **kwargs)


class RateLimitExceededError(AppException):
    """Too many requests from the same client."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
