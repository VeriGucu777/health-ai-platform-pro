"""Immutable evaluation context and result models (no I/O, no PHI-heavy defaults)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.clinical_decision.enums import (
    ClinicalInputSource,
    EvaluationStatus,
    MissingInformationCriticality,
    QuestionType,
    SafetyAlertSeverity,
    TriggeredInputType,
)
from app.domain.clinical_knowledge.enums import KNOWN_SPECIALTY_KEYS


class BaseFrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PatientDemographicsInput(BaseFrozenModel):
    age_years: int | None = Field(default=None, ge=0, le=130)
    gender_key: str | None = Field(default=None, max_length=32)


class EncounterComplaintInput(BaseFrozenModel):
    complaint_key: str = Field(min_length=1, max_length=128)
    negated: bool = False
    source: ClinicalInputSource = ClinicalInputSource.PATIENT_REPORTED
    recorded_at: datetime | None = None


class ClinicalFindingInput(BaseFrozenModel):
    finding_key: str = Field(min_length=1, max_length=128)
    value_code: str | None = Field(default=None, max_length=64)
    negated: bool = False
    source: ClinicalInputSource = ClinicalInputSource.CLINICIAN_OBSERVED
    recorded_at: datetime | None = None


class VitalObservationInput(BaseFrozenModel):
    vital_key: str = Field(min_length=1, max_length=64)
    value_numeric: float | None = None
    unit: str | None = Field(default=None, max_length=32)
    source: ClinicalInputSource = ClinicalInputSource.DEVICE
    recorded_at: datetime | None = None


class QuestionResponseInput(BaseFrozenModel):
    question_key: str = Field(min_length=1, max_length=128)
    answer_code: str = Field(min_length=1, max_length=128)
    recorded_at: datetime | None = None


class EncounterHistoricalContext(BaseFrozenModel):
    """Summary-only history slice; full bundle is assembled in application layer."""

    has_measurements: bool = False
    has_medical_records: bool = False
    has_risk_history: bool = False
    has_appointments: bool = False


class EncounterEvaluationContext(BaseFrozenModel):
    encounter_id: UUID
    patient_id: UUID
    organization_id: UUID | None
    clinician_user_id: UUID
    specialty_key: str = Field(min_length=1, max_length=64)
    locale: Literal["tr", "en"]
    patient_demographics: PatientDemographicsInput
    chief_complaints: tuple[EncounterComplaintInput, ...] = Field(default_factory=tuple)
    findings: tuple[ClinicalFindingInput, ...] = Field(default_factory=tuple)
    vitals: tuple[VitalObservationInput, ...] = Field(default_factory=tuple)
    question_responses: tuple[QuestionResponseInput, ...] = Field(default_factory=tuple)
    historical_context: EncounterHistoricalContext | None = None
    context_version: str = Field(min_length=1, max_length=64)
    created_at: datetime
    input_snapshot_id: str | None = Field(default=None, max_length=128)

    @field_validator("specialty_key")
    @classmethod
    def specialty_must_be_known(cls, value: str) -> str:
        if value not in KNOWN_SPECIALTY_KEYS:
            msg = f"unsupported specialty_key: {value!r}"
            raise ValueError(msg)
        return value


class GuidelineProvenanceRef(BaseFrozenModel):
    source_id: str = Field(min_length=1, max_length=128)
    section_ref: str = Field(min_length=1, max_length=128)
    recommendation_id: str | None = Field(default=None, max_length=128)


class TriggeredByRef(BaseFrozenModel):
    input_type: TriggeredInputType
    input_key: str = Field(min_length=1, max_length=128)
    value_summary: str | None = Field(default=None, max_length=128)

    @field_validator("value_summary")
    @classmethod
    def bounded_value_summary(cls, value: str | None) -> str | None:
        if value is not None and len(value.split()) > 16:
            msg = "value_summary must be a short normalized category, not free-text PHI"
            raise ValueError(msg)
        return value


class ClinicalDecisionProvenance(BaseFrozenModel):
    rule_id: str | None = Field(default=None, max_length=128)
    rule_version: str | None = Field(default=None, max_length=64)
    source_refs: tuple[str, ...] = Field(default_factory=tuple)
    guideline_refs: tuple[GuidelineProvenanceRef, ...] = Field(default_factory=tuple)
    engine_version: str = Field(min_length=1, max_length=64)
    specialty_module_version: str = Field(min_length=1, max_length=64)
    policy_profile_id: str = Field(min_length=1, max_length=128)
    policy_profile_version: str = Field(min_length=1, max_length=64)
    rule_set_manifest_hash: str = Field(min_length=1, max_length=128)
    input_snapshot_id: str | None = Field(default=None, max_length=128)
    sequence_no: int = Field(default=0, ge=0)
    evaluated_at: datetime
    clinical_review_version: str | None = Field(default=None, max_length=64)
    triggered_by: tuple[TriggeredByRef, ...] = Field(default_factory=tuple)


class DifferentialCandidateOutput(BaseFrozenModel):
    condition_key: str = Field(min_length=1, max_length=128)
    display_key: str = Field(min_length=1, max_length=256)
    rank: int = Field(ge=1, le=1000)
    relative_priority_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence: tuple[str, ...] = Field(default_factory=tuple)
    opposing_evidence: tuple[str, ...] = Field(default_factory=tuple)
    explanation_key: str = Field(min_length=1, max_length=256)
    rationale_key: str = Field(min_length=1, max_length=256)
    provenance: ClinicalDecisionProvenance

    @model_validator(mode="after")
    def rule_provenance_required(self) -> DifferentialCandidateOutput:
        if not self.provenance.rule_id or not self.provenance.rule_version:
            msg = "rule-derived differential output requires provenance.rule_id and rule_version"
            raise ValueError(msg)
        return self


class SuggestedQuestionOutput(BaseFrozenModel):
    question_key: str = Field(min_length=1, max_length=128)
    display_key: str = Field(min_length=1, max_length=256)
    rationale_key: str = Field(min_length=1, max_length=256)
    priority: int = Field(ge=0, le=1000)
    question_type: QuestionType
    provenance: ClinicalDecisionProvenance


class MissingInformationOutput(BaseFrozenModel):
    data_element_key: str = Field(min_length=1, max_length=128)
    display_key: str = Field(min_length=1, max_length=256)
    rationale_key: str = Field(min_length=1, max_length=256)
    priority: int = Field(ge=0, le=1000)
    criticality: MissingInformationCriticality
    provenance: ClinicalDecisionProvenance


class SafetyAlertOutput(BaseFrozenModel):
    alert_key: str = Field(min_length=1, max_length=128)
    display_key: str = Field(min_length=1, max_length=256)
    severity: SafetyAlertSeverity
    rationale_key: str = Field(min_length=1, max_length=256)
    trigger_summary: str = Field(min_length=1, max_length=256)
    provenance: ClinicalDecisionProvenance


class ClinicalDecisionEvaluationResult(BaseFrozenModel):
    evaluation_id: UUID
    encounter_id: UUID
    engine_version: str = Field(min_length=1, max_length=64)
    specialty_module_version: str = Field(min_length=1, max_length=64)
    policy_profile_id: str = Field(min_length=1, max_length=128)
    policy_profile_version: str = Field(min_length=1, max_length=64)
    rule_set_manifest_hash: str = Field(min_length=1, max_length=128)
    evaluated_at: datetime
    evaluation_status: EvaluationStatus
    differential_candidates: tuple[DifferentialCandidateOutput, ...] = Field(default_factory=tuple)
    suggested_questions: tuple[SuggestedQuestionOutput, ...] = Field(default_factory=tuple)
    missing_information: tuple[MissingInformationOutput, ...] = Field(default_factory=tuple)
    safety_alerts: tuple[SafetyAlertOutput, ...] = Field(default_factory=tuple)


class SpecialtyEvaluationSlice(BaseFrozenModel):
    """Internal specialty module output before policy merge."""

    differential_candidates: tuple[DifferentialCandidateOutput, ...] = Field(default_factory=tuple)
    suggested_questions: tuple[SuggestedQuestionOutput, ...] = Field(default_factory=tuple)
    missing_information: tuple[MissingInformationOutput, ...] = Field(default_factory=tuple)
    safety_alerts: tuple[SafetyAlertOutput, ...] = Field(default_factory=tuple)
