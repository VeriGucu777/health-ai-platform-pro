"""httpx mock transport for external narrative HTTP scenarios."""

from __future__ import annotations

import json
from typing import Any

import httpx


def _chat_response(content: dict[str, Any]) -> httpx.Response:
    body = {
        "choices": [{"message": {"content": json.dumps(content)}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200},
    }
    return httpx.Response(200, json=body)


def valid_structured_response(*, evidence_id: str, summary: str, lang_hint: str = "") -> dict[str, Any]:
    text = summary or f"Summary citing evidence ({lang_hint})"
    return {
        "summary": text,
        "key_findings": [{"text": text, "source_evidence_ids": [evidence_id]}],
        "risk_context": [],
        "follow_up_context": [],
        "uncertainties": [],
        "source_evidence_ids": [evidence_id],
    }


def transport_valid(evidence_id: str, summary: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_response(valid_structured_response(evidence_id=evidence_id, summary=summary))

    return httpx.MockTransport(handler)


def transport_dynamic_valid(summary: str) -> httpx.MockTransport:
    """Return structured output referencing the first evidence_id in the outbound request."""

    def handler(request: httpx.Request) -> httpx.Response:
        posted = json.loads(request.content)
        user_payload = json.loads(posted["messages"][1]["content"])
        items = user_payload.get("evidence_items") or []
        eid = items[0]["evidence_id"] if items else "health_measurement:00000000-0000-0000-0000-000000000001"
        return _chat_response(valid_structured_response(evidence_id=eid, summary=summary))

    return httpx.MockTransport(handler)


def transport_status(status_code: int) -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "upstream failure"})

    return httpx.MockTransport(handler)


def transport_invalid_json() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    return httpx.MockTransport(handler)


def transport_malformed_schema() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [{"message": {"content": '{"summary": 123}'}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def transport_hallucinated_id(real_id: str) -> httpx.MockTransport:
    fake = "medical_record:00000000-0000-0000-0000-000000000099"

    def handler(_request: httpx.Request) -> httpx.Response:
        return _chat_response(
            {
                "summary": "Patient has confirmed diagnosis of rare syndrome",
                "key_findings": [
                    {"text": "Confirmed diagnosis", "source_evidence_ids": [fake]},
                ],
                "source_evidence_ids": [fake],
            },
        )

    return httpx.MockTransport(handler)


def transport_timeout() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout")

    return httpx.MockTransport(handler)
