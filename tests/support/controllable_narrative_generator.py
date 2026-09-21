"""Controllable narrative generator for unit/API tests."""

from __future__ import annotations

from app.application.clinical_narrative.exceptions import ClinicalNarrativeProviderError
from app.application.dtos.clinical_narrative import (
    ClinicalNarrativeFindingDTO,
    ClinicalNarrativeStructuredLLMOutput,
)
from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGenerator,
    ClinicalNarrativeGeneratorInfo,
    ClinicalNarrativeGeneratorInput,
)


class ControllableNarrativeGenerator(ClinicalNarrativeGenerator):
    """Inject structured outputs or failures in tests."""

    def __init__(self) -> None:
        self.mode: str = "valid"
        self.custom_output: ClinicalNarrativeStructuredLLMOutput | None = None

    def provider_info(self) -> ClinicalNarrativeGeneratorInfo:
        return ClinicalNarrativeGeneratorInfo(provider_kind="fake", model_identifier="controllable_v1")

    async def generate(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> ClinicalNarrativeStructuredLLMOutput:
        if self.mode == "timeout":
            raise ClinicalNarrativeProviderError("Simulated provider timeout")
        if self.mode == "invalid_json":
            raise ClinicalNarrativeProviderError("Simulated invalid structured output")
        if self.custom_output is not None:
            return self.custom_output
        if self.mode == "hallucinated_id":
            return ClinicalNarrativeStructuredLLMOutput(
                summary="Bad summary",
                key_findings=[
                    ClinicalNarrativeFindingDTO(
                        text="Claim without valid evidence",
                        source_evidence_ids=["medical_record:00000000-0000-0000-0000-000000000099"],
                    ),
                ],
                source_evidence_ids=["medical_record:00000000-0000-0000-0000-000000000099"],
            )
        if self.mode == "unsupported_diagnosis":
            return ClinicalNarrativeStructuredLLMOutput(
                summary="Patient is diagnosed with imaginary syndrome",
                key_findings=[
                    ClinicalNarrativeFindingDTO(
                        text="Patient has confirmed diagnosis of rare disease",
                        source_evidence_ids=[payload.evidence_items[0].evidence_id],
                    ),
                ],
                source_evidence_ids=[payload.evidence_items[0].evidence_id],
            )
        if self.mode == "medication":
            return ClinicalNarrativeStructuredLLMOutput(
                summary="Recommend treatment",
                key_findings=[
                    ClinicalNarrativeFindingDTO(
                        text="Prescribe 500mg metformin daily",
                        source_evidence_ids=[payload.evidence_items[0].evidence_id],
                    ),
                ],
                source_evidence_ids=[payload.evidence_items[0].evidence_id],
            )
        if not payload.evidence_items:
            return ClinicalNarrativeStructuredLLMOutput(summary="No evidence", source_evidence_ids=[])
        eid = payload.evidence_items[0].evidence_id
        return ClinicalNarrativeStructuredLLMOutput(
            summary="Valid controlled summary",
            key_findings=[ClinicalNarrativeFindingDTO(text="Finding", source_evidence_ids=[eid])],
            source_evidence_ids=[eid],
        )
