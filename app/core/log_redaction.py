"""Log redaction helpers to avoid leaking secrets and PHI."""

from __future__ import annotations

import logging
import re

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_PHONE_PATTERN = re.compile(r"\b\+?\d{10,15}\b")

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_BEARER_PATTERN, "Bearer [REDACTED]"),
    (_JWT_PATTERN, "[REDACTED_JWT]"),
    (_EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    (_PHONE_PATTERN, "[REDACTED_PHONE]"),
)


def redact_sensitive_text(message: str) -> str:
    """Mask common secret and PHI patterns in a log message."""
    redacted = message
    for pattern, replacement in _REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class SensitiveDataFilter(logging.Filter):
    """Apply redaction to every log record message."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            record.args = tuple(
                redact_sensitive_text(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True
