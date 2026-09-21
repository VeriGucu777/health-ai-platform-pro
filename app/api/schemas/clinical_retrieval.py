"""Clinical retrieval API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.clinical_retrieval.constants import DEFAULT_TOP_K, MAX_TOP_K, RETRIEVAL_VERSION
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


class PatientClinicalRetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    source_types: list[ClinicalEvidenceSourceType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ClinicalRetrievalResultResponse(BaseModel):
    evidence_id: str
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None = None
    relevance_score: float
    content_fields: dict[str, str]

    model_config = ConfigDict(from_attributes=True)


class PatientClinicalRetrievalResponse(BaseModel):
    patient_id: UUID
    retrieval_version: str = RETRIEVAL_VERSION
    query_received: bool
    top_k: int
    results: list[ClinicalRetrievalResultResponse]

    model_config = ConfigDict(from_attributes=True)
