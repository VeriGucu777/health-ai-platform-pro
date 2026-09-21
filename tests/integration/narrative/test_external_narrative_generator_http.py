"""External narrative generator HTTP scenarios (mock transport, production config shape)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.application.clinical_narrative.exceptions import (
    ClinicalNarrativeHallucinationError,
    ClinicalNarrativeProviderError,
)
from app.application.clinical_narrative.validator import ClinicalNarrativeValidator
from app.core.config import Settings
from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGeneratorInput,
    ClinicalNarrativeEvidenceItem,
)
from app.infrastructure.llm.external_narrative_generator import ExternalClinicalNarrativeGenerator
from tests.support.external_narrative_mock_transport import (
    transport_dynamic_valid,
    transport_hallucinated_id,
    transport_invalid_json,
    transport_malformed_schema,
    transport_status,
    transport_timeout,
)
from tests.support.synthetic_narrative_evidence import synthetic_retrieval_bundle
from app.application.clinical_narrative.evidence_payload import build_evidence_items


def _external_settings(**overrides) -> Settings:
    base = dict(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        CLINICAL_NARRATIVE_PROVIDER="external",
        CLINICAL_NARRATIVE_EXTERNAL_BASE_URL="https://llm.example/v1",
        CLINICAL_NARRATIVE_EXTERNAL_API_KEY="test-key-not-real",
        CLINICAL_NARRATIVE_EXTERNAL_MODEL="gpt-test-narrative",
        CLINICAL_NARRATIVE_TIMEOUT_SECONDS=5,
        CLINICAL_NARRATIVE_MAX_RETRIES=1,
        CLINICAL_NARRATIVE_MAX_OUTPUT_TOKENS=800,
    )
    base.update(overrides)
    return Settings(**base)


def _generator_input(*, language: str = "en", query: str = "overview") -> ClinicalNarrativeGeneratorInput:
    hits = synthetic_retrieval_bundle()
    items = build_evidence_items(hits, max_items=10)
    return ClinicalNarrativeGeneratorInput(
        prompt_version="clinical_narrative_prompt_v1",
        language=language,  # type: ignore[arg-type]
        user_query_intent=query,
        evidence_items=items,
        max_output_tokens=800,
    )


@pytest.mark.asyncio
async def test_external_valid_structured_response() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_dynamic_valid("Synthetic glucose and diabetes follow-up context."),
    )
    payload = _generator_input(language="en")
    structured = await gen.generate(payload)
    assert structured.summary
    assert set(structured.source_evidence_ids).issubset({i.evidence_id for i in payload.evidence_items})
    ClinicalNarrativeValidator().validate(
        structured,
        allowed_evidence_ids={i.evidence_id for i in payload.evidence_items},
        evidence_items=payload.evidence_items,
    )


@pytest.mark.asyncio
async def test_external_payload_minimizes_phi() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_dynamic_valid("ok"),
    )
    payload = _generator_input()
    await gen.generate(payload)
    assert gen.last_outbound_request is not None
    raw = json.dumps(gen.last_outbound_request, ensure_ascii=False)
    assert "MustNotAppear" not in raw
    assert "+15550009999" not in raw
    assert "first_name" not in raw.lower()
    user_blob = gen.last_outbound_request["messages"][1]["content"]
    assert "Ignore previous instructions" in user_blob
    assert "MustNotAppear" not in user_blob


@pytest.mark.asyncio
async def test_external_hallucinated_id_fails_validator() -> None:
    hits = synthetic_retrieval_bundle()
    real_id = hits[0].evidence_id
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_hallucinated_id(real_id),
    )
    payload = _generator_input()
    structured = await gen.generate(payload)
    with pytest.raises(ClinicalNarrativeHallucinationError):
        ClinicalNarrativeValidator().validate(
            structured,
            allowed_evidence_ids={i.evidence_id for i in payload.evidence_items},
            evidence_items=payload.evidence_items,
        )


@pytest.mark.asyncio
async def test_external_timeout_raises_provider_error() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_timeout(),
    )
    with pytest.raises(ClinicalNarrativeProviderError):
        await gen.generate(_generator_input())


@pytest.mark.asyncio
async def test_external_5xx_raises_provider_error() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_status(503),
    )
    with pytest.raises(ClinicalNarrativeProviderError):
        await gen.generate(_generator_input())


@pytest.mark.asyncio
async def test_external_invalid_json_raises_provider_error() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_invalid_json(),
    )
    with pytest.raises(ClinicalNarrativeProviderError, match="invalid structured"):
        await gen.generate(_generator_input())


@pytest.mark.asyncio
async def test_external_malformed_schema_raises_provider_error() -> None:
    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(),
        http_transport=transport_malformed_schema(),
    )
    with pytest.raises(ClinicalNarrativeProviderError):
        await gen.generate(_generator_input())


@pytest.mark.asyncio
async def test_external_5xx_bounded_retries() -> None:
    attempts: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(502, json={"error": "bad gateway"})

    gen = ExternalClinicalNarrativeGenerator(
        _external_settings(CLINICAL_NARRATIVE_MAX_RETRIES=1),
        http_transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ClinicalNarrativeProviderError):
        await gen.generate(_generator_input())
    assert len(attempts) == 2
