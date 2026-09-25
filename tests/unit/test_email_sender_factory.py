"""Email sender factory wiring and production safety."""

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.email.email_sender_factory import get_email_sender
from app.infrastructure.email.logging_email_sender import LoggingEmailSender
from app.infrastructure.email.postmark_email_sender import PostmarkEmailSender
from app.infrastructure.email.recording_email_sender import RecordingEmailSender


def test_factory_postmark_returns_postmark_sender() -> None:
    settings = Settings(
        EMAIL_PROVIDER="postmark",
        POSTMARK_SERVER_TOKEN="pm-test-token",
        EMAIL_FROM_ADDRESS="verify@example.com",
    )
    sender = get_email_sender(settings)
    assert isinstance(sender, PostmarkEmailSender)


def test_factory_logging_returns_logging_sender() -> None:
    for provider in ("logging", "noop", "none"):
        settings = Settings(EMAIL_PROVIDER=provider)
        sender = get_email_sender(settings)
        assert isinstance(sender, LoggingEmailSender)


def test_factory_recording_returns_recording_sender() -> None:
    settings = Settings(EMAIL_PROVIDER="recording")
    sender = get_email_sender(settings)
    assert isinstance(sender, RecordingEmailSender)


def test_factory_production_unknown_provider_fail_fast() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        EMAIL_PROVIDER="postmrak",
    )
    with pytest.raises(ConfigurationError, match="Unsupported EMAIL_PROVIDER"):
        get_email_sender(settings)


def test_factory_development_unknown_provider_falls_back_to_logging() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_PROVIDER="postmrak",
    )
    sender = get_email_sender(settings)
    assert isinstance(sender, LoggingEmailSender)


def test_factory_postmark_requires_server_token() -> None:
    settings = Settings(
        EMAIL_PROVIDER="postmark",
        POSTMARK_SERVER_TOKEN="",
        EMAIL_FROM_ADDRESS="verify@example.com",
    )
    with pytest.raises(ConfigurationError, match="POSTMARK_SERVER_TOKEN"):
        get_email_sender(settings)


def test_factory_postmark_requires_from_address() -> None:
    settings = Settings(
        EMAIL_PROVIDER="postmark",
        POSTMARK_SERVER_TOKEN="pm-test-token",
        EMAIL_FROM_ADDRESS="",
    )
    with pytest.raises(ConfigurationError, match="EMAIL_FROM_ADDRESS"):
        get_email_sender(settings)
