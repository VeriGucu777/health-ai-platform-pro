"""Deterministic fake narrative generator for tests and development."""

from __future__ import annotations

from app.application.dtos.clinical_narrative import (
    ClinicalNarrativeFindingDTO,
    ClinicalNarrativeStructuredLLMOutput,
)
from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGenerator,
    ClinicalNarrativeGeneratorInfo,
    ClinicalNarrativeGeneratorInput,
)


class DeterministicFakeNarrativeGenerator(ClinicalNarrativeGenerator):
    """Produce predictable structured output citing provided evidence ids."""

    def provider_info(self) -> ClinicalNarrativeGeneratorInfo:
        return ClinicalNarrativeGeneratorInfo(
            provider_kind="fake",
            model_identifier="deterministic_fake_narrative_v1",
        )

    async def generate(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> ClinicalNarrativeStructuredLLMOutput:
        if not payload.evidence_items:
            return ClinicalNarrativeStructuredLLMOutput(
                summary=(
                    "No clinical evidence items were available for narrative synthesis."
                    if payload.language == "en"
                    else "Anlatı sentezi için klinik kanıt bulunamadı."
                ),
                uncertainties=["not available"],
                source_evidence_ids=[],
            )

        primary_id = payload.evidence_items[0].evidence_id
        all_ids = [item.evidence_id for item in payload.evidence_items]
        summary = (
            f"Overview based on {len(all_ids)} evidence item(s)."
            if payload.language == "en"
            else f"{len(all_ids)} kanıt öğesine dayalı genel bakış."
        )
        finding_text = (
            f"Evidence snapshot: {payload.evidence_items[0].clinical_text[:240]}"
            if payload.language == "en"
            else f"Kanıt özeti: {payload.evidence_items[0].clinical_text[:240]}"
        )
        return ClinicalNarrativeStructuredLLMOutput(
            summary=summary,
            key_findings=[
                ClinicalNarrativeFindingDTO(
                    text=finding_text,
                    source_evidence_ids=[primary_id],
                ),
            ],
            source_evidence_ids=all_ids,
        )
