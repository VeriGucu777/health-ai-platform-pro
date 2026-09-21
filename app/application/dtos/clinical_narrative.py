"""Clinical narrative DTOs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.application.clinical_narrative.constants import (
    CLINICAL_NARRATIVE_DISCLAIMER,
    NARRATIVE_VERSION,
)
from app.application.dtos.base import BaseSchema
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


class ClinicalNarrativeFindingDTO(BaseSchema):
    text: str
    source_evidence_ids: list[str] = Field(min_length=1)


class ClinicalNarrativeStructuredLLMOutput(BaseSchema):
    """Schema requested from the LLM provider."""

    summary: str
    key_findings: list[ClinicalNarrativeFindingDTO] = Field(default_factory=list)
    risk_context: list[ClinicalNarrativeFindingDTO] = Field(default_factory=list)
    follow_up_context: list[ClinicalNarrativeFindingDTO] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)


class ClinicalNarrativeEvidenceReferenceDTO(BaseSchema):
    evidence_id: str
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None = None


class PatientClinicalNarrativeDTO(BaseSchema):
    patient_id: UUID
    narrative_version: str = NARRATIVE_VERSION
    generated_at: datetime
    narrative: str
    evidence_references: list[ClinicalNarrativeEvidenceReferenceDTO]
    limitations: list[str]
    disclaimer: str = CLINICAL_NARRATIVE_DISCLAIMER
    fallback_used: bool = False
    prompt_version: str
    language: Literal["tr", "en"]
