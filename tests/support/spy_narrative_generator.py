"""Spy wrapper for narrative generator call counts."""

from __future__ import annotations

from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGenerator,
    ClinicalNarrativeGeneratorInfo,
    ClinicalNarrativeGeneratorInput,
)
from app.application.dtos.clinical_narrative import ClinicalNarrativeStructuredLLMOutput


class SpyNarrativeGenerator(ClinicalNarrativeGenerator):
    def __init__(self, inner: ClinicalNarrativeGenerator) -> None:
        self._inner = inner
        self.generate_calls = 0

    def provider_info(self) -> ClinicalNarrativeGeneratorInfo:
        return self._inner.provider_info()

    async def generate(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> ClinicalNarrativeStructuredLLMOutput:
        self.generate_calls += 1
        return await self._inner.generate(payload)
