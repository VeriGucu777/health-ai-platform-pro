"""Outbound email port (verification and transactional)."""

from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    """Send transactional email without exposing provider details to application services."""

    async def send_verification_email(
        self,
        *,
        to_email: str,
        verify_url: str,
        locale: str = "en",
    ) -> None: ...
