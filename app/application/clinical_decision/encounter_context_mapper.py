"""Map ClinicalEncounterAggregate (+ optional vitals) to EncounterEvaluationContext."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.application.clinical_decision.exceptions import (
    EncounterContextAssemblyValidationError,
    UnknownClinicalVocabularyKeyError,
)
from app.application.clinical_decision.vocabulary_eligibility import (
    VocabularyEligibilityMode,
    term_eligible_for_assembly,
)
from app.domain.clinical_decision.enums import ClinicalInputSource as DecisionInputSource
from app.domain.clinical_decision.models import (
    ClinicalFindingInput,
    EncounterComplaintInput,
    EncounterEvaluationContext,
    EncounterHistoricalContext,
    PatientDemographicsInput,
    QuestionResponseInput,
    VitalObservationInput,
)
from app.domain.clinical_encounter.entities import (
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinding,
    EncounterQuestionResponse,
)
from app.domain.clinical_encounter.enums import ClinicalInputSource as EncounterInputSource
from app.domain.clinical_encounter.enums import QuestionAnswerType
from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.entities.health_measurement import HealthMeasurement

_CONTEXT_VERSION = "encounter-evaluation-context-v1"

_PHI_SENTINEL_FIELDS = frozenset(
    {
        "clinician_display_text",
        "clinician_note",
        "clinician_text",
        "summary_sections",
        "notes",
    },
)


@dataclass(frozen=True, slots=True)
class EncounterContextAssemblyRequest:
    """Inputs for read-only evaluation context assembly (no I/O)."""

    aggregate: ClinicalEncounterAggregate
    patient_demographics: PatientDemographicsInput
    historical_context: EncounterHistoricalContext | None = None
    health_measurements: tuple[HealthMeasurement, ...] = ()
    locale: Literal["tr", "en"] | None = None
    reference_at: datetime | None = None
    vocabulary_registry: ClinicalVocabularyRegistry | None = None
    vocabulary_mode: VocabularyEligibilityMode = VocabularyEligibilityMode.DEMO
    validate_vocabulary_keys: bool = True


def _is_active_child(*, is_active: bool, deleted_at: datetime | None) -> bool:
    return is_active and deleted_at is None


def _map_finding_source(source: EncounterInputSource) -> DecisionInputSource:
    if source == EncounterInputSource.PATIENT_REPORTED:
        return DecisionInputSource.PATIENT_REPORTED
    if source == EncounterInputSource.DEVICE:
        return DecisionInputSource.DEVICE
    if source == EncounterInputSource.HISTORICAL_RECORD:
        return DecisionInputSource.RECORD
    if source == EncounterInputSource.CLINICIAN_OBSERVED:
        return DecisionInputSource.CLINICIAN_OBSERVED
    return DecisionInputSource.CLINICIAN_OBSERVED


def _validate_vocabulary_key(
    registry: ClinicalVocabularyRegistry,
    key: str,
    category: VocabularyCategory,
    mode: VocabularyEligibilityMode,
) -> None:
    item = registry.get(key)
    if item is None:
        raise UnknownClinicalVocabularyKeyError(
            f"unknown vocabulary key {key!r} for category {category.value}",
        )
    if item.category != category:
        raise UnknownClinicalVocabularyKeyError(
            f"key {key!r} is category {item.category.value}, expected {category.value}",
        )
    if not term_eligible_for_assembly(item, mode):
        raise UnknownClinicalVocabularyKeyError(
            f"vocabulary key {key!r} is not eligible for assembly mode {mode.value}",
        )


def _maybe_validate_key(
    registry: ClinicalVocabularyRegistry | None,
    key: str,
    category: VocabularyCategory,
    mode: VocabularyEligibilityMode,
    validate: bool,
) -> None:
    if not validate or registry is None:
        return
    _validate_vocabulary_key(registry, key, category, mode)


def _vocabulary_answer_code_key(answer_code: str) -> str:
    """Encounter boolean answers use yes/no/unknown; vocabulary uses card.answer_code.*."""
    normalized = answer_code.strip().lower()
    if normalized in ("yes", "no", "unknown"):
        return f"card.answer_code.{normalized}"
    return answer_code


def _numeric_to_float(value: Decimal | int | float) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _map_complaints(
    complaints: tuple[EncounterComplaint, ...],
    registry: ClinicalVocabularyRegistry | None,
    mode: VocabularyEligibilityMode,
    validate: bool,
) -> tuple[EncounterComplaintInput, ...]:
    active = [
        c
        for c in complaints
        if _is_active_child(is_active=c.is_active, deleted_at=c.deleted_at) and c.complaint_key
    ]
    active.sort(key=lambda c: (c.sequence_no, c.id))
    mapped: list[EncounterComplaintInput] = []
    for complaint in active:
        key = complaint.complaint_key
        assert key is not None
        _maybe_validate_key(registry, key, VocabularyCategory.COMPLAINT, mode, validate)
        mapped.append(
            EncounterComplaintInput(
                complaint_key=key,
                negated=complaint.negated,
                source=DecisionInputSource.PATIENT_REPORTED,
                recorded_at=complaint.recorded_at,
            ),
        )
    return tuple(mapped)


def _map_findings(
    findings: tuple[EncounterFinding, ...],
    registry: ClinicalVocabularyRegistry | None,
    mode: VocabularyEligibilityMode,
    validate: bool,
) -> tuple[ClinicalFindingInput, ...]:
    active = [
        f for f in findings if _is_active_child(is_active=f.is_active, deleted_at=f.deleted_at)
    ]
    active.sort(key=lambda f: (f.sequence_no, f.id))
    mapped: list[ClinicalFindingInput] = []
    for finding in active:
        _maybe_validate_key(registry, finding.finding_key, VocabularyCategory.FINDING, mode, validate)
        if finding.onset_code and validate and registry is not None:
            _maybe_validate_key(registry, finding.onset_code, VocabularyCategory.ONSET, mode, validate)
        mapped.append(
            ClinicalFindingInput(
                finding_key=finding.finding_key,
                value_code=finding.value_code,
                negated=finding.negated,
                source=_map_finding_source(finding.source),
                recorded_at=finding.recorded_at,
            ),
        )
    return tuple(mapped)


def _map_question_responses(
    responses: tuple[EncounterQuestionResponse, ...],
    registry: ClinicalVocabularyRegistry | None,
    mode: VocabularyEligibilityMode,
    validate: bool,
) -> tuple[QuestionResponseInput, ...]:
    active = [
        r
        for r in responses
        if _is_active_child(is_active=r.is_active, deleted_at=r.deleted_at)
        and r.is_engine_evaluable()
        and r.answer_code
    ]
    active.sort(key=lambda r: (r.sequence_no, r.id))
    mapped: list[QuestionResponseInput] = []
    for response in active:
        _maybe_validate_key(registry, response.question_key, VocabularyCategory.QUESTION, mode, validate)
        answer_code = response.answer_code
        assert answer_code is not None
        vocab_answer_key = _vocabulary_answer_code_key(answer_code)
        _maybe_validate_key(registry, vocab_answer_key, VocabularyCategory.ANSWER_CODE, mode, validate)
        mapped.append(
            QuestionResponseInput(
                question_key=response.question_key,
                answer_code=answer_code,
                recorded_at=response.answered_at,
            ),
        )
    return tuple(mapped)


@dataclass(frozen=True, slots=True)
class _VitalFieldSpec:
    vital_key: str
    unit_label: str


_VITAL_SPECS: tuple[tuple[str, _VitalFieldSpec], ...] = (
    ("systolic_pressure", _VitalFieldSpec("card.vital.systolic_blood_pressure", "mmHg")),
    ("diastolic_pressure", _VitalFieldSpec("card.vital.diastolic_blood_pressure", "mmHg")),
    ("heart_rate", _VitalFieldSpec("card.vital.heart_rate", "bpm")),
)


def _map_health_measurements(
    measurements: tuple[HealthMeasurement, ...],
    registry: ClinicalVocabularyRegistry | None,
    mode: VocabularyEligibilityMode,
    validate: bool,
) -> tuple[VitalObservationInput, ...]:
    active = [
        m
        for m in measurements
        if m.is_active and m.deleted_at is None
    ]
    active.sort(key=lambda m: (m.measured_at, m.id))
    vitals: list[VitalObservationInput] = []
    for measurement in active:
        for field_name, spec in _VITAL_SPECS:
            raw = getattr(measurement, field_name)
            if raw is None:
                continue
            _maybe_validate_key(registry, spec.vital_key, VocabularyCategory.VITAL, mode, validate)
            vitals.append(
                VitalObservationInput(
                    vital_key=spec.vital_key,
                    value_numeric=_numeric_to_float(raw),
                    unit=spec.unit_label,
                    source=DecisionInputSource.DEVICE,
                    recorded_at=measurement.measured_at,
                ),
            )
    return tuple(vitals)


def assemble_encounter_evaluation_context(
    request: EncounterContextAssemblyRequest,
) -> EncounterEvaluationContext:
    """Build a frozen evaluation context from encounter structured inputs only."""
    encounter = request.aggregate.encounter
    if encounter.locale not in ("tr", "en"):
        raise EncounterContextAssemblyValidationError(
            f"unsupported encounter locale: {encounter.locale!r}",
        )
    locale: Literal["tr", "en"] = request.locale or encounter.locale  # type: ignore[assignment]

    registry = request.vocabulary_registry
    mode = request.vocabulary_mode
    validate = request.validate_vocabulary_keys

    complaints = _map_complaints(request.aggregate.complaints, registry, mode, validate)
    findings = _map_findings(request.aggregate.findings, registry, mode, validate)
    question_responses = _map_question_responses(
        request.aggregate.question_responses,
        registry,
        mode,
        validate,
    )
    vitals = _map_health_measurements(
        request.health_measurements,
        registry,
        mode,
        validate,
    )

    if request.aggregate.final_summary is not None:
        pass  # intentionally excluded from engine evaluation context

    created_at = request.reference_at or datetime.now(UTC)
    if created_at.tzinfo is None:
        raise EncounterContextAssemblyValidationError("reference_at must be timezone-aware")

    snapshot_id = f"{encounter.id}:v{encounter.version}"

    return EncounterEvaluationContext(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        organization_id=encounter.organization_id,
        clinician_user_id=encounter.clinician_user_id,
        specialty_key=encounter.specialty_key,
        locale=locale,
        patient_demographics=request.patient_demographics,
        chief_complaints=complaints,
        findings=findings,
        vitals=vitals,
        question_responses=question_responses,
        historical_context=request.historical_context,
        context_version=_CONTEXT_VERSION,
        created_at=created_at,
        input_snapshot_id=snapshot_id,
    )


def context_contains_forbidden_phi_markers(context: EncounterEvaluationContext) -> bool:
    """Test helper: detect PHI field names in serialized context (not values from aggregate text)."""
    payload = context.model_dump_json()
    lowered = payload.lower()
    for marker in _PHI_SENTINEL_FIELDS:
        if marker in lowered:
            return True
    return False
