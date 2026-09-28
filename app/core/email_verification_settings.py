"""EMAIL_VERIFICATION_PEPPER validation for staging/production when enforcement is on."""

from __future__ import annotations

from typing import TYPE_CHECKING

INSECURE_EMAIL_VERIFICATION_PEPPERS: frozenset[str] = frozenset(
    {
        "",
        "dev-email-verification-pepper-change-me",
        "change-me",
        "changeme",
        "email-verification-pepper",
    }
)

MIN_EMAIL_VERIFICATION_PEPPER_LENGTH = 32


def email_verification_pepper_validation_error(environment: str) -> str:
    return (
        f"EMAIL_VERIFICATION_PEPPER is missing, too short, or uses a default value for "
        f"{environment} while EMAIL_VERIFICATION_ENFORCED is true. "
        f"Set a unique pepper of at least {MIN_EMAIL_VERIFICATION_PEPPER_LENGTH} characters."
    )


def is_insecure_email_verification_pepper(pepper: str) -> bool:
    normalized = pepper.strip()
    if not normalized:
        return True
    if normalized.lower() in INSECURE_EMAIL_VERIFICATION_PEPPERS:
        return True
    return len(normalized) < MIN_EMAIL_VERIFICATION_PEPPER_LENGTH


def validate_email_verification_settings(settings: "Settings") -> None:
    from app.core.config import Settings

    if not isinstance(settings, Settings):
        raise TypeError("settings must be a Settings instance")
    if not settings.email_verification_enforced:
        return
    if settings.environment not in {"staging", "production"}:
        return
    if is_insecure_email_verification_pepper(settings.email_verification_pepper):
        raise ValueError(email_verification_pepper_validation_error(settings.environment))


if TYPE_CHECKING:
    from app.core.config import Settings
