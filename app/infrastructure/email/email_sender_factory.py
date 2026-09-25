"""Construct EmailSender implementations from settings."""

from __future__ import annotations

from app.core.config import Settings
from app.domain.interfaces.email_sender import EmailSender
from app.infrastructure.email.logging_email_sender import LoggingEmailSender
from app.infrastructure.email.recording_email_sender import RecordingEmailSender


def get_email_sender(settings: Settings) -> EmailSender:
    """Return the configured email sender (no external providers in pilot)."""
    provider = (settings.email_provider or "logging").strip().lower()
    if provider == "recording":
        return RecordingEmailSender()
    if provider in {"logging", "noop", "none"}:
        return LoggingEmailSender()
    # Future: smtp, resend, postmark adapters.
    return LoggingEmailSender()
