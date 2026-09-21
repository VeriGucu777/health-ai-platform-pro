"""Patient clinical summary API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.reference_ranges import CLINICAL_SUMMARY_DISCLAIMER
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


class ClinicalEvidenceProvenanceResponse(BaseModel):
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    occurred_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalSummaryDataWindowResponse(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalItemResponse(BaseModel):
    item_type: str
    label: str
    detail: str
    provenance: ClinicalEvidenceProvenanceResponse

    model_config = ConfigDict(from_attributes=True)


class RecentMeasurementResponse(BaseModel):
    metric_type: str
    value: str
    unit: str
    measured_at: datetime
    provenance: ClinicalEvidenceProvenanceResponse

    model_config = ConfigDict(from_attributes=True)


class EncounterResponse(BaseModel):
    appointment_id: UUID
    appointment_date: datetime
    appointment_type: str
    status: str
    timing: str
    provenance: ClinicalEvidenceProvenanceResponse

    model_config = ConfigDict(from_attributes=True)


class LatestRiskAssessmentResponse(BaseModel):
    assessment_type: str
    assessment_status: str
    risk_level: str | None = None
    score: float | None = None
    probability: float | None = None
    evaluated_at: datetime
    model_kind: str
    model_version: str
    provenance: ClinicalEvidenceProvenanceResponse

    model_config = ConfigDict(from_attributes=True)


class CareFlagResponse(BaseModel):
    flag_type: str
    message: str
    provenance: ClinicalEvidenceProvenanceResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalSummaryDataQualityResponse(BaseModel):
    no_data: bool
    missing_sections: list[str]
    last_available_date: datetime | None = None
    stale_sections: list[str]

    model_config = ConfigDict(from_attributes=True)


class PatientClinicalSummaryResponse(BaseModel):
    patient_id: UUID
    generated_at: datetime
    summary_version: str
    data_window: ClinicalSummaryDataWindowResponse
    clinical_items: list[ClinicalItemResponse]
    recent_measurements: list[RecentMeasurementResponse]
    encounters: list[EncounterResponse]
    latest_risk_assessments: list[LatestRiskAssessmentResponse]
    care_flags: list[CareFlagResponse]
    data_quality: ClinicalSummaryDataQualityResponse
    disclaimer: str = Field(
        default=CLINICAL_SUMMARY_DISCLAIMER,
        description="Mandatory decision-support disclaimer for the clinical summary.",
    )

    model_config = ConfigDict(from_attributes=True)
