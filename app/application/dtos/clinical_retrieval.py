"""Clinical retrieval API DTOs."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


class ClinicalRetrievalResultDTO(BaseSchema):
    evidence_id: str
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None = None
    relevance_score: float
    content_fields: dict[str, str]


class PatientClinicalRetrievalDTO(BaseSchema):
    patient_id: UUID
    retrieval_version: str
    query_received: bool
    top_k: int
    results: list[ClinicalRetrievalResultDTO]
