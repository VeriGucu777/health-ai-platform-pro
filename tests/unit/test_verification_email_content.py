"""Verification email copy and locale normalization."""

from app.infrastructure.email.verification_email_content import (
    build_verification_email,
    contains_phi_markers,
    normalize_locale,
)


def test_normalize_locale_tr_variants() -> None:
    assert normalize_locale("tr") == "tr"
    assert normalize_locale("tr-TR") == "tr"


def test_normalize_locale_fallback_en() -> None:
    assert normalize_locale("") == "en"
    assert normalize_locale("de") == "en"


def test_build_verification_email_includes_url_only_once_in_plain_text() -> None:
    url = "https://app.example.com/verify-email?token=abc"
    _, text, _ = build_verification_email(verify_url=url, locale="en")
    assert url in text
    assert not contains_phi_markers(text)
