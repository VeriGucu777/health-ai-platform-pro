"""External HTTP LLM provider (explicit opt-in, env-configured)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.application.clinical_narrative.exceptions import ClinicalNarrativeProviderError
from app.application.clinical_narrative.prompt_v1 import system_prompt
from app.application.dtos.clinical_narrative import ClinicalNarrativeStructuredLLMOutput
from app.core.config import Settings
from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGenerator,
    ClinicalNarrativeGeneratorInfo,
    ClinicalNarrativeGeneratorInput,
)

logger = logging.getLogger(__name__)


class ExternalClinicalNarrativeGenerator(ClinicalNarrativeGenerator):
    """OpenAI-compatible chat completions with JSON-only structured output."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._http_transport = http_transport
        self.last_outbound_request: dict[str, Any] | None = None
        if not settings.clinical_narrative_external_api_key.strip():
            raise ClinicalNarrativeProviderError("External narrative provider API key is not configured")
        if not settings.clinical_narrative_external_model.strip():
            raise ClinicalNarrativeProviderError("External narrative model is not configured")
        if not settings.clinical_narrative_external_base_url.strip():
            raise ClinicalNarrativeProviderError("External narrative base URL is not configured")

    def provider_info(self) -> ClinicalNarrativeGeneratorInfo:
        return ClinicalNarrativeGeneratorInfo(
            provider_kind="external",
            model_identifier=self._settings.clinical_narrative_external_model.strip(),
        )

    def build_chat_request_body(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> dict[str, Any]:
        user_content = self._build_user_content(payload)
        return {
            "model": self._settings.clinical_narrative_external_model.strip(),
            "messages": [
                {"role": "system", "content": system_prompt(language=payload.language)},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": min(
                payload.max_output_tokens,
                self._settings.clinical_narrative_max_output_tokens,
            ),
            "temperature": 0,
        }

    async def generate(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> ClinicalNarrativeStructuredLLMOutput:
        body = self.build_chat_request_body(payload)
        self.last_outbound_request = body
        url = self._settings.clinical_narrative_external_base_url.rstrip("/") + "/chat/completions"
        timeout = httpx.Timeout(self._settings.clinical_narrative_timeout_seconds)
        last_error: Exception | None = None
        max_attempts = self._settings.clinical_narrative_max_retries + 1
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout, transport=self._http_transport) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self._settings.clinical_narrative_external_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                if response.status_code >= 500:
                    raise ClinicalNarrativeProviderError(
                        f"External narrative provider returned {response.status_code}",
                    )
                if response.status_code >= 400:
                    raise ClinicalNarrativeProviderError(
                        f"External narrative provider rejected request ({response.status_code})",
                    )
                data = response.json()
                usage = data.get("usage")
                if isinstance(usage, dict):
                    logger.info(
                        "Clinical narrative external tokens prompt=%s completion=%s total=%s",
                        usage.get("prompt_tokens"),
                        usage.get("completion_tokens"),
                        usage.get("total_tokens"),
                    )
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                structured = ClinicalNarrativeStructuredLLMOutput.model_validate(parsed)
                logger.info(
                    "Clinical narrative external generation success provider=external model=%s evidence_count=%s",
                    self.provider_info().model_identifier,
                    len(payload.evidence_items),
                )
                return structured
            except ClinicalNarrativeProviderError as exc:
                last_error = exc
                retryable = "returned 5" in exc.message
                if retryable and attempt < max_attempts - 1:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    break
                await asyncio.sleep(0.2 * (2**attempt))
            except (KeyError, json.JSONDecodeError, ValueError, PydanticValidationError) as exc:
                raise ClinicalNarrativeProviderError("External narrative returned invalid structured output") from exc

        raise ClinicalNarrativeProviderError("External narrative provider unavailable") from last_error

    @staticmethod
    def _build_user_content(payload: ClinicalNarrativeGeneratorInput) -> str:
        return json.dumps(
            {
                "user_query_intent": payload.user_query_intent,
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "source_type": item.source_type,
                        "event_time": item.event_time_iso,
                        "clinical_text": item.clinical_text,
                    }
                    for item in payload.evidence_items
                ],
            },
            ensure_ascii=False,
        )
