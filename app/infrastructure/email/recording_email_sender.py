"""In-memory email sender for tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecordedVerificationEmail:
    to_email: str
    verify_url: str
    locale: str


class RecordingEmailSender:
    """Captures verification emails without network I/O."""

    def __init__(self) -> None:
        self.sent: list[RecordedVerificationEmail] = []

    async def send_verification_email(
        self,
        *,
        to_email: str,
        verify_url: str,
        locale: str = "en",
    ) -> None:
        self.sent.append(
            RecordedVerificationEmail(
                to_email=to_email,
                verify_url=verify_url,
                locale=locale,
            ),
        )
