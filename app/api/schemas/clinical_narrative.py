"""Clinical narrative API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.clinical_narrative.constants import (
    CLINICAL_NARRATIVE_DISCLAIMER,
    DEFAULT_MAX_NARRATIVE_EVIDENCE,
    MAX_NARRATIVE_EVIDENCE,
    MAX_QUERY_LENGTH,
    NARRATIVE_VERSION,
)
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


class PatientClinicalNarrativeRequest(BaseModel):
    query: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    date_from: datetime | None = None
    date_to: datetime | None = None
    source_types: list[ClinicalEvidenceSourceType] | None = None
    max_evidence: int = Field(default=DEFAULT_MAX_NARRATIVE_EVIDENCE, ge=1, le=MAX_NARRATIVE_EVIDENCE)
    language: Literal["tr", "en"] | None = None


class ClinicalNarrativeEvidenceReferenceResponse(BaseModel):
    evidence_id: str
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientClinicalNarrativeResponse(BaseModel):
    patient_id: UUID
    narrative_version: str = NARRATIVE_VERSION
    generated_at: datetime
    narrative: str
    evidence_references: list[ClinicalNarrativeEvidenceReferenceResponse]
    limitations: list[str]
    disclaimer: str = CLINICAL_NARRATIVE_DISCLAIMER
    fallback_used: bool
    prompt_version: str
    language: Literal["tr", "en"]

    model_config = ConfigDict(from_attributes=True)
