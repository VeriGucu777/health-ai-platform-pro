"""Verification email copy (no PHI — transactional only)."""

from __future__ import annotations

from html import escape

PRODUCT_NAME = "Health AI Platform Pro"

_PHI_MARKERS = (
    "diagnosis",
    "risk score",
    "patient",
    "clinical",
    "tanı",
    "hasta",
    "risk skoru",
)


def normalize_locale(locale: str) -> str:
    """Map locale to supported verification template language."""
    normalized = (locale or "en").strip().lower()
    if normalized.startswith("tr"):
        return "tr"
    return "en"


def build_verification_email(*, verify_url: str, locale: str) -> tuple[str, str, str]:
    """Return subject, plain-text body, and HTML body for a verification message."""
    lang = normalize_locale(locale)
    if lang == "tr":
        subject = f"{PRODUCT_NAME} — E-posta adresinizi doğrulayın"
        text_body = (
            f"{PRODUCT_NAME}\n\n"
            "E-posta adresinizi doğrulayın.\n"
            "Hesabınızı etkinleştirmek için aşağıdaki doğrulama bağlantısını kullanın.\n"
            "Bağlantı sınırlı süre geçerlidir.\n\n"
            f"{verify_url}\n\n"
            "Bu kaydı siz yapmadıysanız bu e-postayı yok sayabilirsiniz."
        )
        safe_url = escape(verify_url, quote=True)
        html_body = (
            f"<p><strong>{PRODUCT_NAME}</strong></p>"
            "<p>E-posta adresinizi doğrulayın.</p>"
            "<p>Hesabınızı etkinleştirmek için doğrulama bağlantısına tıklayın. "
            "Bağlantı sınırlı süre geçerlidir.</p>"
            f'<p><a href="{safe_url}">E-postamı doğrula</a></p>'
            "<p>Bu kaydı siz yapmadıysanız bu e-postayı yok sayabilirsiniz.</p>"
        )
    else:
        subject = f"{PRODUCT_NAME} — Verify your email address"
        text_body = (
            f"{PRODUCT_NAME}\n\n"
            "Verify your email address.\n"
            "Use the verification link below to activate your account.\n"
            "The link is valid for a limited time.\n\n"
            f"{verify_url}\n\n"
            "If you did not create this account, you can ignore this email."
        )
        safe_url = escape(verify_url, quote=True)
        html_body = (
            f"<p><strong>{PRODUCT_NAME}</strong></p>"
            "<p>Verify your email address.</p>"
            "<p>Click the verification link below to activate your account. "
            "The link is valid for a limited time.</p>"
            f'<p><a href="{safe_url}">Verify my email</a></p>'
            "<p>If you did not create this account, you can ignore this email.</p>"
        )
    return subject, text_body, html_body


def contains_phi_markers(text: str) -> bool:
    """True if text includes clinical/patient content markers (guardrail for tests)."""
    lowered = text.lower()
    return any(marker in lowered for marker in _PHI_MARKERS)
