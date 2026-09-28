"""EMAIL_VERIFICATION_PEPPER fail-fast when enforcement is on in staging/production."""

import pytest

from app.core.config import Settings, get_settings
from app.core.email_verification_settings import validate_email_verification_settings

STRONG_PEPPER = "x" * 40


def test_production_enforced_missing_pepper_fails() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="x" * 40,
        DEBUG=False,
        CORS_ORIGINS=["https://app.example.com"],
        EMAIL_VERIFICATION_ENFORCED=True,
        EMAIL_VERIFICATION_PEPPER="",
    )
    with pytest.raises(ValueError, match="EMAIL_VERIFICATION_PEPPER"):
        validate_email_verification_settings(settings)


def test_production_enforced_default_pepper_fails() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="x" * 40,
        DEBUG=False,
        CORS_ORIGINS=["https://app.example.com"],
        EMAIL_VERIFICATION_ENFORCED=True,
        EMAIL_VERIFICATION_PEPPER="dev-email-verification-pepper-change-me",
    )
    with pytest.raises(ValueError, match="EMAIL_VERIFICATION_PEPPER"):
        validate_email_verification_settings(settings)


def test_production_enforced_strong_pepper_passes() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="x" * 40,
        DEBUG=False,
        CORS_ORIGINS=["https://app.example.com"],
        EMAIL_VERIFICATION_ENFORCED=True,
        EMAIL_VERIFICATION_PEPPER=STRONG_PEPPER,
    )
    validate_email_verification_settings(settings)


def test_development_enforced_weak_pepper_allowed() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        EMAIL_VERIFICATION_ENFORCED=True,
        EMAIL_VERIFICATION_PEPPER="dev-email-verification-pepper-change-me",
    )
    validate_email_verification_settings(settings)


def test_get_settings_production_enforced_weak_pepper(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "y" * 40)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("EMAIL_VERIFICATION_ENFORCED", "true")
    monkeypatch.setenv("EMAIL_VERIFICATION_PEPPER", "dev-email-verification-pepper-change-me")
    with pytest.raises(ValueError, match="EMAIL_VERIFICATION_PEPPER"):
        get_settings()
    get_settings.cache_clear()
