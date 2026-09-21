"""Port for LLM clinical narrative generation — no database access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from app.application.dtos.clinical_narrative import ClinicalNarrativeStructuredLLMOutput


@dataclass(frozen=True)
class ClinicalNarrativeEvidenceItem:
    """PHI-minimized evidence slice passed to the LLM."""

    evidence_id: str
    source_type: str
    event_time_iso: str | None
    clinical_text: str


@dataclass(frozen=True)
class ClinicalNarrativeGeneratorInput:
    """Inputs for narrative generation — evidence-only, no patient identity fields."""

    prompt_version: str
    language: Literal["tr", "en"]
    user_query_intent: str
    evidence_items: list[ClinicalNarrativeEvidenceItem] = field(default_factory=list)
    max_output_tokens: int = 1024


@dataclass(frozen=True)
class ClinicalNarrativeGeneratorInfo:
    """Non-PHI provider descriptor for audit/logging."""

    provider_kind: str
    model_identifier: str


class ClinicalNarrativeGenerator(ABC):
    """Generate structured clinical narrative from authorized evidence only."""

    @abstractmethod
    async def generate(
        self,
        payload: ClinicalNarrativeGeneratorInput,
    ) -> ClinicalNarrativeStructuredLLMOutput:
        """Return structured LLM output or raise ClinicalNarrativeProviderError."""

    @abstractmethod
    def provider_info(self) -> ClinicalNarrativeGeneratorInfo:
        """Return provider kind and model id for audit (no secrets)."""
