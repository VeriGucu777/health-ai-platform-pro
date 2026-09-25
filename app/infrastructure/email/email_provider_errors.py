"""Errors raised by outbound email provider adapters."""


class EmailProviderError(Exception):
    """Email could not be delivered via the configured provider."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        reason_code: str,
        status_code: int | None = None,
    ) -> None:
        self.provider = provider
        self.reason_code = reason_code
        self.status_code = status_code
        super().__init__(message)
