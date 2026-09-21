"""Clinical evidence bundle and future retrieval contract DTOs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.application.dtos.base import BaseSchema
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory


class ClinicalEvidenceProvenanceDTO(BaseSchema):
    """Traceability metadata for one summarized item."""

    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    occurred_at: datetime | None = None


class ClinicalRetrievalDocumentDTO(BaseSchema):
    """Internal RAG-ready document shape (not exposed on public summary API)."""

    evidence_id: str
    patient_id: UUID
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None = None
    content_fields: dict[str, Any] = Field(default_factory=dict)
    organization_id: UUID | None = None
    access_scope: str = "patient_read"


@dataclass
class ClinicalEvidenceBundle:
    """Authorized clinical evidence collected for one patient."""

    patient: Patient
    organization_id: UUID | None = None
    medical_records: list[MedicalRecord] = field(default_factory=list)
    health_measurements: list[HealthMeasurement] = field(default_factory=list)
    appointments: list[Appointment] = field(default_factory=list)
    risk_assessment_history: list[RiskAssessmentHistory] = field(default_factory=list)
    retrieval_documents: list[ClinicalRetrievalDocumentDTO] = field(default_factory=list)
