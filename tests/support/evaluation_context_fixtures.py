"""Neutral EncounterEvaluationContext fixtures for snapshot and future rule tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.clinical_decision.enums import ClinicalInputSource
from app.domain.clinical_decision.models import (
    ClinicalFindingInput,
    EncounterComplaintInput,
    EncounterEvaluationContext,
    EncounterHistoricalContext,
    PatientDemographicsInput,
    QuestionResponseInput,
    VitalObservationInput,
)

_FIXTURE_ENCOUNTER_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
_FIXTURE_PATIENT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_FIXTURE_ORG_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
_FIXTURE_CLINICIAN_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
_T1 = datetime(2026, 3, 1, 10, 15, tzinfo=UTC)
_ASSEMBLY_VERSION = "encounter-evaluation-context-v1"


def _base_context(**overrides: object) -> EncounterEvaluationContext:
    base = {
        "encounter_id": _FIXTURE_ENCOUNTER_ID,
        "patient_id": _FIXTURE_PATIENT_ID,
        "organization_id": _FIXTURE_ORG_ID,
        "clinician_user_id": _FIXTURE_CLINICIAN_ID,
        "specialty_key": "cardiology",
        "locale": "tr",
        "patient_demographics": PatientDemographicsInput(),
        "chief_complaints": (),
        "findings": (),
        "vitals": (),
        "question_responses": (),
        "historical_context": None,
        "context_version": _ASSEMBLY_VERSION,
        "created_at": _T0,
        "input_snapshot_id": None,
    }
    base.update(overrides)
    return EncounterEvaluationContext.model_validate(base)


def minimal_evaluation_context() -> EncounterEvaluationContext:
    return _base_context()


def context_with_complaint() -> EncounterEvaluationContext:
    return _base_context(
        chief_complaints=(
            EncounterComplaintInput(
                complaint_key="card.complaint.chest_pain",
                negated=False,
                source=ClinicalInputSource.PATIENT_REPORTED,
                recorded_at=_T0,
            ),
        ),
    )


def context_with_negated_finding() -> EncounterEvaluationContext:
    return _base_context(
        findings=(
            ClinicalFindingInput(
                finding_key="card.finding.smoking_history",
                negated=True,
                source=ClinicalInputSource.CLINICIAN_OBSERVED,
                recorded_at=_T0,
            ),
        ),
    )


def context_with_vital() -> EncounterEvaluationContext:
    return _base_context(
        vitals=(
            VitalObservationInput(
                vital_key="card.vital.heart_rate",
                value_numeric=72.0,
                unit="bpm",
                source=ClinicalInputSource.DEVICE,
                recorded_at=_T1,
            ),
        ),
    )


def context_with_question_response() -> EncounterEvaluationContext:
    return _base_context(
        question_responses=(
            QuestionResponseInput(
                question_key="card.question.chest_pain_on_exertion",
                answer_code="yes",
                recorded_at=_T0,
            ),
        ),
    )


def context_with_historical_flags() -> EncounterEvaluationContext:
    return _base_context(
        historical_context=EncounterHistoricalContext(
            has_measurements=True,
            has_medical_records=False,
            has_risk_history=True,
            has_appointments=False,
        ),
    )
