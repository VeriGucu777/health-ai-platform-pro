"""Deterministic patient clinical summary DTOs."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.application.dtos.clinical_evidence import ClinicalEvidenceProvenanceDTO


class ClinicalSummaryDataWindowDTO(BaseSchema):
    date_from: datetime | None = None
    date_to: datetime | None = None


class ClinicalItemDTO(BaseSchema):
    item_type: str
    label: str
    detail: str
    provenance: ClinicalEvidenceProvenanceDTO


class RecentMeasurementDTO(BaseSchema):
    metric_type: str
    value: str
    unit: str
    measured_at: datetime
    provenance: ClinicalEvidenceProvenanceDTO


class EncounterDTO(BaseSchema):
    appointment_id: UUID
    appointment_date: datetime
    appointment_type: str
    status: str
    timing: str
    provenance: ClinicalEvidenceProvenanceDTO


class LatestRiskAssessmentDTO(BaseSchema):
    assessment_type: str
    assessment_status: str
    risk_level: str | None = None
    score: float | None = None
    probability: float | None = None
    evaluated_at: datetime
    model_kind: str
    model_version: str
    provenance: ClinicalEvidenceProvenanceDTO


class CareFlagDTO(BaseSchema):
    flag_type: str
    message: str
    provenance: ClinicalEvidenceProvenanceDTO | None = None


class ClinicalSummaryDataQualityDTO(BaseSchema):
    no_data: bool
    missing_sections: list[str]
    last_available_date: datetime | None = None
    stale_sections: list[str]


class PatientClinicalSummaryDTO(BaseSchema):
    patient_id: UUID
    generated_at: datetime
    summary_version: str
    data_window: ClinicalSummaryDataWindowDTO
    clinical_items: list[ClinicalItemDTO]
    recent_measurements: list[RecentMeasurementDTO]
    encounters: list[EncounterDTO]
    latest_risk_assessments: list[LatestRiskAssessmentDTO]
    care_flags: list[CareFlagDTO]
    data_quality: ClinicalSummaryDataQualityDTO
    disclaimer: str
