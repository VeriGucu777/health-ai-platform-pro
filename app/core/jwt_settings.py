"""JWT secret validation helpers for environment-aware settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

INSECURE_JWT_SECRETS: frozenset[str] = frozenset(
    {
        "",
        "change-me",
        "change-me-to-a-long-random-secret-in-production",
        "changeme",
        "jwt-secret",
        "jwt_secret",
        "secret",
        "your-secret-key",
    }
)

MIN_JWT_SECRET_LENGTH_NON_DEV = 32


def is_insecure_jwt_secret(secret: str) -> bool:
    """Return True when a JWT secret is empty, too short, or a known default."""
    normalized = secret.strip()
    if not normalized:
        return True
    if normalized.lower() in INSECURE_JWT_SECRETS:
        return True
    return len(normalized) < MIN_JWT_SECRET_LENGTH_NON_DEV


def jwt_secret_validation_error(environment: str) -> str:
    """Return a safe validation message that never includes the secret value."""
    return (
        f"JWT_SECRET_KEY is missing, too short, or uses a default value for "
        f"{environment}. Set a unique secret of at least "
        f"{MIN_JWT_SECRET_LENGTH_NON_DEV} characters."
    )


def validate_settings_security(settings: "Settings") -> None:
    """Reject insecure JWT configuration outside development."""
    from app.core.config import Settings

    if not isinstance(settings, Settings):
        raise TypeError("settings must be a Settings instance")

    if settings.environment in {"staging", "production"} and is_insecure_jwt_secret(
        settings.jwt_secret_key,
    ):
        raise ValueError(jwt_secret_validation_error(settings.environment))


if TYPE_CHECKING:
    from app.core.config import Settings
