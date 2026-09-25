"""FRONTEND_PUBLIC_URL production HTTPS validation."""

import pytest

from app.application.services.email_verification_service import EmailVerificationService
from app.core.config import Settings
from app.core.frontend_public_url import validate_and_normalize_frontend_public_url
from app.infrastructure.email.recording_email_sender import RecordingEmailSender
from tests.support.memory_email_verification_token_repository import (
    InMemoryEmailVerificationTokenRepository,
)
from tests.support.memory_user_repository import InMemoryUserRepository


def test_production_https_url_allowed() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="x" * 32,
        CORS_ORIGINS=["https://app.example.com"],
        FRONTEND_PUBLIC_URL="https://app.example.com/",
    )
    normalized = validate_and_normalize_frontend_public_url(settings)
    assert normalized.frontend_public_url == "https://app.example.com"


def test_production_http_url_rejected() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="x" * 32,
        CORS_ORIGINS=["https://app.example.com"],
        FRONTEND_PUBLIC_URL="http://app.example.com",
    )
    with pytest.raises(ValueError, match="https://"):
        validate_and_normalize_frontend_public_url(settings)


def test_production_malformed_url_rejected() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="x" * 32,
        CORS_ORIGINS=["https://app.example.com"],
        FRONTEND_PUBLIC_URL="not-a-valid-url",
    )
    with pytest.raises(ValueError, match="valid absolute"):
        validate_and_normalize_frontend_public_url(settings)


def test_development_localhost_http_allowed() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        FRONTEND_PUBLIC_URL="http://localhost:3000/",
    )
    normalized = validate_and_normalize_frontend_public_url(settings)
    assert normalized.frontend_public_url == "http://localhost:3000"


@pytest.mark.asyncio
async def test_trailing_slash_produces_single_slash_verify_path() -> None:
    settings = Settings(
        FRONTEND_PUBLIC_URL="http://localhost:3000/",
        EMAIL_VERIFICATION_PEPPER="test-pepper",
    )
    service = EmailVerificationService(
        InMemoryUserRepository(),
        InMemoryEmailVerificationTokenRepository(),
        email_sender=RecordingEmailSender(),
        settings=settings,
    )
    url = service._build_verify_url("sample-token")
    assert url == "http://localhost:3000/verify-email?token=sample-token"
    assert "//verify" not in url.replace("://", "")
