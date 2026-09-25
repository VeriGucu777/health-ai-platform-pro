"""Postmark email adapter tests (HTTP mocked — no real API calls)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.infrastructure.email.email_provider_errors import EmailProviderError
from app.infrastructure.email.postmark_email_sender import (
    POSTMARK_EMAIL_ENDPOINT,
    POSTMARK_SERVER_TOKEN_HEADER,
    PostmarkEmailSender,
)
from app.infrastructure.email.verification_email_content import (
    build_verification_email,
    contains_phi_markers,
)

SERVER_TOKEN = "pm-test-server-token-for-unit-tests"
FROM_ADDRESS = "Health AI <verify@example.com>"
VERIFY_URL = "https://app.example.com/verify-email?token=raw-token-value-for-test"
RAW_TOKEN = "raw-token-value-for-test"


def _postmark_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_postmark_sends_to_correct_endpoint() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        return httpx.Response(200, json={"MessageID": "test-id", "ErrorCode": 0})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    await sender.send_verification_email(
        to_email="user@example.com",
        verify_url=VERIFY_URL,
        locale="en",
    )
    assert seen["url"] == POSTMARK_EMAIL_ENDPOINT
    assert seen["method"] == "POST"


@pytest.mark.asyncio
async def test_postmark_includes_server_token_header_not_in_logs(caplog) -> None:
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers["token"] = request.headers.get(POSTMARK_SERVER_TOKEN_HEADER, "")
        return httpx.Response(200, json={"MessageID": "ok"})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    with caplog.at_level("INFO"):
        await sender.send_verification_email(
            to_email="user@example.com",
            verify_url=VERIFY_URL,
            locale="en",
        )

    assert captured_headers["token"] == SERVER_TOKEN
    log_blob = "\n".join(r.message for r in caplog.records)
    assert SERVER_TOKEN not in log_blob
    assert RAW_TOKEN not in log_blob


@pytest.mark.asyncio
async def test_postmark_payload_from_recipient_and_verify_url() -> None:
    body: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"MessageID": "ok"})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    await sender.send_verification_email(
        to_email="recipient@example.com",
        verify_url=VERIFY_URL,
        locale="en",
    )
    assert body["From"] == FROM_ADDRESS
    assert body["To"] == "recipient@example.com"
    assert VERIFY_URL in body["TextBody"]
    assert VERIFY_URL in body["HtmlBody"]


@pytest.mark.asyncio
async def test_postmark_en_template() -> None:
    body: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"MessageID": "ok"})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    await sender.send_verification_email(
        to_email="user@example.com",
        verify_url=VERIFY_URL,
        locale="en",
    )
    assert "Verify your email address" in body["Subject"]
    assert "Health AI Platform Pro" in body["TextBody"]


@pytest.mark.asyncio
async def test_postmark_tr_template() -> None:
    body: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"MessageID": "ok"})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    await sender.send_verification_email(
        to_email="user@example.com",
        verify_url=VERIFY_URL,
        locale="tr",
    )
    assert "E-posta adresinizi doğrulayın" in body["Subject"]
    assert "Hesabınızı etkinleştirmek için" in body["TextBody"]


def test_verification_templates_contain_no_phi_markers() -> None:
    for locale in ("en", "tr"):
        subject, text, html = build_verification_email(verify_url=VERIFY_URL, locale=locale)
        combined = f"{subject}\n{text}\n{html}"
        assert not contains_phi_markers(combined)


@pytest.mark.asyncio
async def test_postmark_success_on_2xx() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"MessageID": "ok"})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    await sender.send_verification_email(
        to_email="user@example.com",
        verify_url=VERIFY_URL,
        locale="en",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_postmark_auth_errors(status_code: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"ErrorCode": status_code})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    with pytest.raises(EmailProviderError) as exc_info:
        await sender.send_verification_email(
            to_email="user@example.com",
            verify_url=VERIFY_URL,
            locale="en",
        )
    assert exc_info.value.reason_code == "provider_auth"
    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_postmark_5xx_raises_provider_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"ErrorCode": 503})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    with pytest.raises(EmailProviderError) as exc_info:
        await sender.send_verification_email(
            to_email="user@example.com",
            verify_url=VERIFY_URL,
            locale="en",
        )
    assert exc_info.value.reason_code == "provider_unavailable"


@pytest.mark.asyncio
async def test_postmark_timeout_raises_safe_error(caplog) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        timeout_seconds=0.01,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with caplog.at_level("ERROR"):
        with pytest.raises(EmailProviderError) as exc_info:
            await sender.send_verification_email(
                to_email="user@example.com",
                verify_url=VERIFY_URL,
                locale="en",
            )
    assert exc_info.value.reason_code == "timeout"
    log_blob = "\n".join(r.message for r in caplog.records)
    assert SERVER_TOKEN not in log_blob
    assert RAW_TOKEN not in log_blob


@pytest.mark.asyncio
async def test_postmark_error_logs_exclude_secrets(caplog) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"ErrorCode": 500})

    sender = PostmarkEmailSender(
        server_token=SERVER_TOKEN,
        from_address=FROM_ADDRESS,
        http_client=httpx.AsyncClient(transport=_postmark_transport(handler)),
    )
    with caplog.at_level("ERROR"):
        with pytest.raises(EmailProviderError):
            await sender.send_verification_email(
                to_email="user@example.com",
                verify_url=VERIFY_URL,
                locale="en",
            )
    log_blob = "\n".join(r.message for r in caplog.records)
    assert SERVER_TOKEN not in log_blob
    assert RAW_TOKEN not in log_blob
    assert "Authorization" not in log_blob
