"""Development email sender that logs delivery without exposing secrets."""

from __future__ import annotations

from app.core.logging import get_logger

_logger = get_logger(__name__)


class LoggingEmailSender:
    """Log verification email dispatch metadata only (no token, no password)."""

    async def send_verification_email(
        self,
        *,
        to_email: str,
        verify_url: str,
        locale: str = "en",
    ) -> None:
        _logger.info(
            "Verification email queued recipient_domain=%s locale=%s",
            to_email.split("@")[-1] if "@" in to_email else "unknown",
            locale,
        )
