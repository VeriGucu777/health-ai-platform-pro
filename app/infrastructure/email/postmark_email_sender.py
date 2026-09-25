"""Postmark transactional email adapter for verification messages."""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.infrastructure.email.email_provider_errors import EmailProviderError
from app.infrastructure.email.verification_email_content import build_verification_email

_logger = get_logger(__name__)

POSTMARK_EMAIL_ENDPOINT = "https://api.postmarkapp.com/email"
POSTMARK_SERVER_TOKEN_HEADER = "X-Postmark-Server-Token"


class PostmarkEmailSender:
    """Send verification email via Postmark HTTP API."""

    def __init__(
        self,
        *,
        server_token: str,
        from_address: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._server_token = server_token
        self._from_address = from_address
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client
        self._owns_client = http_client is None

    async def send_verification_email(
        self,
        *,
        to_email: str,
        verify_url: str,
        locale: str = "en",
    ) -> None:
        subject, text_body, html_body = build_verification_email(
            verify_url=verify_url,
            locale=locale,
        )
        payload: dict[str, str] = {
            "From": self._from_address,
            "To": to_email,
            "Subject": subject,
            "TextBody": text_body,
            "HtmlBody": html_body,
            "MessageStream": "outbound",
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            POSTMARK_SERVER_TOKEN_HEADER: self._server_token,
        }

        client = self._http_client
        close_after = False
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout_seconds)
            close_after = True

        try:
            response = await client.post(
                POSTMARK_EMAIL_ENDPOINT,
                json=payload,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            _logger.error(
                "Postmark verification email failed reason_code=timeout recipient_domain=%s",
                _recipient_domain(to_email),
            )
            raise EmailProviderError(
                "Email provider request timed out",
                provider="postmark",
                reason_code="timeout",
            ) from exc
        except httpx.RequestError as exc:
            _logger.error(
                "Postmark verification email failed reason_code=connection_error recipient_domain=%s",
                _recipient_domain(to_email),
            )
            raise EmailProviderError(
                "Email provider connection failed",
                provider="postmark",
                reason_code="connection_error",
            ) from exc
        finally:
            if close_after:
                await client.aclose()

        if response.status_code in {401, 403}:
            _logger.error(
                "Postmark verification email failed reason_code=provider_auth status_code=%s",
                response.status_code,
            )
            raise EmailProviderError(
                "Email provider rejected credentials",
                provider="postmark",
                reason_code="provider_auth",
                status_code=response.status_code,
            )

        if response.status_code >= 500:
            _logger.error(
                "Postmark verification email failed reason_code=provider_unavailable status_code=%s",
                response.status_code,
            )
            raise EmailProviderError(
                "Email provider temporarily unavailable",
                provider="postmark",
                reason_code="provider_unavailable",
                status_code=response.status_code,
            )

        if response.status_code < 200 or response.status_code >= 300:
            _logger.error(
                "Postmark verification email failed reason_code=provider_rejected status_code=%s",
                response.status_code,
            )
            raise EmailProviderError(
                "Email provider rejected the message",
                provider="postmark",
                reason_code="provider_rejected",
                status_code=response.status_code,
            )

        _logger.info(
            "Postmark verification email queued recipient_domain=%s locale=%s",
            _recipient_domain(to_email),
            locale,
        )


def _recipient_domain(to_email: str) -> str:
    if "@" in to_email:
        return to_email.split("@", 1)[1]
    return "unknown"
