"""Unit tests for log redaction helpers."""

from app.core.log_redaction import redact_sensitive_text


def test_redacts_email_addresses() -> None:
    message = "Contact user@example.com for support"
    assert "[REDACTED_EMAIL]" in redact_sensitive_text(message)
    assert "user@example.com" not in redact_sensitive_text(message)


def test_redacts_bearer_tokens() -> None:
    message = "Authorization Bearer abc.def.ghi failed"
    redacted = redact_sensitive_text(message)
    assert "Bearer [REDACTED]" in redacted
    assert "abc.def.ghi" not in redacted


def test_redacts_jwt_tokens() -> None:
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    redacted = redact_sensitive_text(f"token={token}")
    assert "[REDACTED_JWT]" in redacted
    assert token not in redacted


def test_redacts_phone_numbers() -> None:
    message = "callback on +15550001111"
    redacted = redact_sensitive_text(message)
    assert "[REDACTED_PHONE]" in redacted
    assert "+15550001111" not in redacted
