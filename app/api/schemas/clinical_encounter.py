"""Clinical encounter HTTP request/response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)


class ClinicalEncounterCreate(BaseModel):
    specialty_key: str = Field(min_length=1, max_length=64)
    locale: str = Field(default="en", min_length=2, max_length=8)
    appointment_id: UUID | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ClinicalEncounterSummaryResponse(BaseModel):
    id: UUID
    patient_id: UUID
    organization_id: UUID
    clinician_user_id: UUID
    specialty_key: str
    status: EncounterStatus
    locale: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    appointment_id: UUID | None = None
    version: int

    model_config = ConfigDict(from_attributes=True)


class ClinicalEncounterListResponse(BaseModel):
    items: list[ClinicalEncounterSummaryResponse]
    total: int
    limit: int
    offset: int


class EncounterComplaintResponse(BaseModel):
    id: UUID
    encounter_id: UUID
    complaint_key: str | None = None
    clinician_display_text: str | None = None
    is_primary: bool
    negated: bool
    sequence_no: int
    recorded_at: datetime
    recorded_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EncounterFindingResponse(BaseModel):
    id: UUID
    encounter_id: UUID
    finding_type: FindingType
    finding_key: str
    value_code: str | None = None
    value_numeric: Decimal | None = None
    unit: str | None = None
    negated: bool
    onset_code: str | None = None
    source: ClinicalInputSource
    sequence_no: int
    recorded_at: datetime
    recorded_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EncounterQuestionResponseItem(BaseModel):
    id: UUID
    encounter_id: UUID
    question_key: str
    answer_type: QuestionAnswerType
    answer_code: str | None = None
    answer_numeric: Decimal | None = None
    clinician_note: str | None = None
    sequence_no: int
    answered_at: datetime
    answered_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class EncounterSummarySectionResponse(BaseModel):
    section_key: str
    content_key: str | None = None
    clinician_text: str | None = None


class EncounterFinalSummaryResponse(BaseModel):
    id: UUID
    encounter_id: UUID
    summary_version: int
    summary_sections: list[EncounterSummarySectionResponse]
    clinician_note: str | None = None
    finalized_by: UUID
    finalized_at: datetime
    created_at: datetime


class ClinicalEncounterDetailResponse(BaseModel):
    encounter: ClinicalEncounterSummaryResponse
    complaints: list[EncounterComplaintResponse]
    findings: list[EncounterFindingResponse]
    question_responses: list[EncounterQuestionResponseItem]
    final_summary: EncounterFinalSummaryResponse | None = None


class EncounterComplaintCreate(BaseModel):
    complaint_key: str | None = Field(default=None, max_length=128)
    clinician_display_text: str | None = Field(default=None, max_length=4000)
    is_primary: bool = False
    negated: bool = False

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EncounterFindingCreate(BaseModel):
    finding_type: FindingType
    finding_key: str = Field(min_length=1, max_length=128)
    value_code: str | None = Field(default=None, max_length=128)
    value_numeric: Decimal | None = None
    unit: str | None = Field(default=None, max_length=32)
    negated: bool = False
    onset_code: str | None = Field(default=None, max_length=64)
    source: ClinicalInputSource = ClinicalInputSource.CLINICIAN_OBSERVED

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("value_numeric")
    @classmethod
    def reject_non_finite_numeric(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if not value.is_finite():
            raise ValueError("value_numeric must be finite")
        return value


class EncounterQuestionResponseUpsert(BaseModel):
    answer_type: QuestionAnswerType
    answer_code: str | None = Field(default=None, max_length=128)
    answer_numeric: Decimal | None = None
    clinician_note: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("answer_numeric")
    @classmethod
    def reject_non_finite_numeric(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if not value.is_finite():
            raise ValueError("answer_numeric must be finite")
        return value


class EncounterSummarySectionInput(BaseModel):
    section_key: str = Field(min_length=1, max_length=64)
    content_key: str | None = Field(default=None, max_length=128)
    clinician_text: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EncounterFinalizeRequest(BaseModel):
    expected_version: int = Field(ge=1)
    summary_sections: list[EncounterSummarySectionInput] = Field(min_length=1)
    clinician_note: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EncounterCancelRequest(BaseModel):
    expected_version: int = Field(ge=1)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
