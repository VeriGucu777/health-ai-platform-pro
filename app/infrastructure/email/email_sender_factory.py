"""Construct EmailSender implementations from settings."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.domain.interfaces.email_sender import EmailSender
from app.infrastructure.email.logging_email_sender import LoggingEmailSender
from app.infrastructure.email.postmark_email_sender import PostmarkEmailSender
from app.infrastructure.email.recording_email_sender import RecordingEmailSender

_LOGGING_PROVIDERS = frozenset({"logging", "noop", "none"})
_KNOWN_PROVIDERS = _LOGGING_PROVIDERS | frozenset({"recording", "postmark"})


def get_email_sender(settings: Settings) -> EmailSender:
    """Return the configured email sender for the current environment."""
    provider = (settings.email_provider or "logging").strip().lower()

    if provider == "recording":
        return RecordingEmailSender()

    if provider == "postmark":
        return _build_postmark_sender(settings)

    if provider in _LOGGING_PROVIDERS:
        return LoggingEmailSender()

    if settings.is_production:
        raise ConfigurationError(
            f"Unsupported EMAIL_PROVIDER {provider!r}; verification emails would not be sent",
        )

    return LoggingEmailSender()


def _build_postmark_sender(settings: Settings) -> PostmarkEmailSender:
    token = settings.postmark_server_token.strip()
    from_address = settings.email_from_address.strip()
    if not token:
        raise ConfigurationError(
            "POSTMARK_SERVER_TOKEN is required when EMAIL_PROVIDER=postmark",
        )
    if not from_address:
        raise ConfigurationError(
            "EMAIL_FROM_ADDRESS is required when EMAIL_PROVIDER=postmark",
        )
    return PostmarkEmailSender(
        server_token=token,
        from_address=from_address,
        timeout_seconds=settings.postmark_request_timeout_seconds,
    )


def is_known_email_provider(provider: str) -> bool:
    """Whether the provider string is explicitly supported."""
    return (provider or "logging").strip().lower() in _KNOWN_PROVIDERS
