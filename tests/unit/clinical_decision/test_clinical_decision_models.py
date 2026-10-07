"""Clinical decision DTO validation and safety invariants."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.clinical_decision.enums import (
    MissingInformationCriticality,
    QuestionType,
    SafetyAlertSeverity,
    TriggeredInputType,
)
from app.domain.clinical_decision.models import (
    ClinicalDecisionProvenance,
    DifferentialCandidateOutput,
    EncounterEvaluationContext,
    PatientDemographicsInput,
    SafetyAlertOutput,
    TriggeredByRef,
)


def _minimal_provenance(**overrides: object) -> ClinicalDecisionProvenance:
    base = {
        "rule_id": "TEST-RULE-001",
        "rule_version": "1.0.0",
        "source_refs": ("guideline:esc:htn:2024",),
        "guideline_refs": (),
        "engine_version": "test_engine_v1",
        "specialty_module_version": "cardiology_v0",
        "policy_profile_id": "none",
        "policy_profile_version": "0.0.0",
        "rule_set_manifest_hash": "empty",
        "evaluated_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return ClinicalDecisionProvenance.model_validate(base)


def test_differential_rejects_invalid_rank_and_score() -> None:
    prov = _minimal_provenance()
    with pytest.raises(ValueError):
        DifferentialCandidateOutput(
            condition_key="cond.hypertension",
            display_key="copilot.cond.hypertension",
            rank=0,
            relative_priority_score=0.5,
            explanation_key="copilot.explanation.test",
            rationale_key="copilot.rationale.test",
            provenance=prov,
        )
    with pytest.raises(ValueError):
        DifferentialCandidateOutput(
            condition_key="cond.hypertension",
            display_key="copilot.cond.hypertension",
            rank=1,
            relative_priority_score=1.5,
            explanation_key="copilot.explanation.test",
            rationale_key="copilot.rationale.test",
            provenance=prov,
        )


def test_differential_requires_rule_provenance() -> None:
    prov = _minimal_provenance(rule_id=None, rule_version=None)
    with pytest.raises(ValueError, match="rule-derived differential"):
        DifferentialCandidateOutput(
            condition_key="cond.test",
            display_key="copilot.cond.test",
            rank=1,
            relative_priority_score=0.2,
            explanation_key="copilot.explanation.test",
            rationale_key="copilot.rationale.test",
            provenance=prov,
        )


def test_safety_alert_rejects_invalid_severity() -> None:
    prov = _minimal_provenance(rule_id="R1", rule_version="1.0.0")
    with pytest.raises(ValueError):
        SafetyAlertOutput(
            alert_key="alert.test",
            display_key="copilot.alert.test",
            severity="critical",  # type: ignore[arg-type]
            rationale_key="copilot.rationale.test",
            trigger_summary="normalized_trigger_category",
            provenance=prov,
        )


def test_triggered_by_rejects_long_free_text_summary() -> None:
    with pytest.raises(ValueError, match="value_summary"):
        TriggeredByRef(
            input_type=TriggeredInputType.COMPLAINT,
            input_key="chief_complaint.chest_pain",
            value_summary=" ".join(["word"] * 20),
        )


def test_output_dtos_immutable() -> None:
    prov = _minimal_provenance()
    item = DifferentialCandidateOutput(
        condition_key="cond.test",
        display_key="copilot.cond.test",
        rank=1,
        relative_priority_score=0.3,
        explanation_key="copilot.explanation.test",
        rationale_key="copilot.rationale.test",
        provenance=prov,
    )
    with pytest.raises(Exception):
        item.rank = 2  # type: ignore[misc]


def test_evaluation_context_json_round_trip() -> None:
    ctx = EncounterEvaluationContext(
        encounter_id=uuid4(),
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        locale="en",
        patient_demographics=PatientDemographicsInput(),
        context_version="encounter_eval_context_v1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    restored = EncounterEvaluationContext.model_validate_json(ctx.model_dump_json())
    assert restored == ctx


def test_safety_invariant_no_probability_fields_on_differential() -> None:
    fields = DifferentialCandidateOutput.model_fields
    forbidden = {"probability", "confidence", "diagnosis_confirmed", "prescribe"}
    assert forbidden.isdisjoint(set(fields.keys()))


def test_safety_alert_valid_severity() -> None:
    prov = _minimal_provenance()
    alert = SafetyAlertOutput(
        alert_key="alert.test",
        display_key="copilot.alert.test",
        severity=SafetyAlertSeverity.WARNING,
        rationale_key="copilot.rationale.test",
        trigger_summary="category:bp_elevation",
        provenance=prov,
    )
    assert alert.severity == SafetyAlertSeverity.WARNING


def test_missing_information_criticality_enum() -> None:
    prov = _minimal_provenance()
    from app.domain.clinical_decision.models import MissingInformationOutput

    row = MissingInformationOutput(
        data_element_key="vital.bp_systolic",
        display_key="copilot.missing.bp",
        rationale_key="copilot.rationale.missing",
        priority=1,
        criticality=MissingInformationCriticality.IMPORTANT,
        provenance=prov,
    )
    assert row.criticality == MissingInformationCriticality.IMPORTANT


def test_suggested_question_type_enum() -> None:
    prov = _minimal_provenance()
    from app.domain.clinical_decision.models import SuggestedQuestionOutput

    row = SuggestedQuestionOutput(
        question_key="q.onset",
        display_key="copilot.q.onset",
        rationale_key="copilot.rationale.q",
        priority=1,
        question_type=QuestionType.HISTORY,
        provenance=prov,
    )
    assert row.question_type == QuestionType.HISTORY
