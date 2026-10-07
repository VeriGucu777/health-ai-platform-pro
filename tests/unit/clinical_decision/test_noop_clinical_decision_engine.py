"""NoOp clinical decision engine tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.clinical_decision.noop_clinical_decision_engine import NoOpClinicalDecisionEngine
from app.domain.clinical_decision.constants import (
    NOOP_ENGINE_VERSION,
    POLICY_PROFILE_ID_NONE,
    POLICY_PROFILE_VERSION_NONE,
    RULE_SET_MANIFEST_HASH_EMPTY,
    SPECIALTY_MODULE_VERSION_NONE,
)
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.clinical_decision.models import EncounterEvaluationContext, PatientDemographicsInput


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now_utc(self) -> datetime:
        return self._moment


class FixedEvaluationIds:
    def __init__(self, evaluation_id: UUID) -> None:
        self._evaluation_id = evaluation_id

    def new_evaluation_id(self) -> UUID:
        return self._evaluation_id


def _context(**overrides: object) -> EncounterEvaluationContext:
    base = {
        "encounter_id": uuid4(),
        "patient_id": uuid4(),
        "organization_id": uuid4(),
        "clinician_user_id": uuid4(),
        "specialty_key": "cardiology",
        "locale": "tr",
        "patient_demographics": PatientDemographicsInput(age_years=55, gender_key="female"),
        "context_version": "encounter_eval_context_v1",
        "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return EncounterEvaluationContext.model_validate(base)


def test_noop_engine_deterministic_semantics() -> None:
    fixed_time = datetime(2026, 3, 1, 9, 30, tzinfo=UTC)
    fixed_id = UUID("11111111-1111-4111-8111-111111111111")
    engine = NoOpClinicalDecisionEngine(
        clock=FixedClock(fixed_time),
        evaluation_id_factory=FixedEvaluationIds(fixed_id),
    )
    ctx = _context()
    first = engine.evaluate(ctx)
    second = engine.evaluate(ctx)

    assert first == second
    assert first.evaluation_status == EvaluationStatus.NO_APPLICABLE_RULES
    assert first.engine_version == NOOP_ENGINE_VERSION
    assert first.specialty_module_version == SPECIALTY_MODULE_VERSION_NONE
    assert first.policy_profile_id == POLICY_PROFILE_ID_NONE
    assert first.policy_profile_version == POLICY_PROFILE_VERSION_NONE
    assert first.rule_set_manifest_hash == RULE_SET_MANIFEST_HASH_EMPTY
    assert first.differential_candidates == ()
    assert first.suggested_questions == ()
    assert first.missing_information == ()
    assert first.safety_alerts == ()


def test_empty_valid_context_no_applicable_rules() -> None:
    engine = NoOpClinicalDecisionEngine(
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
        evaluation_id_factory=FixedEvaluationIds(uuid4()),
    )
    result = engine.evaluate(_context())
    assert result.evaluation_status == EvaluationStatus.NO_APPLICABLE_RULES


def test_invalid_specialty_rejected_at_context_build() -> None:
    with pytest.raises(ValueError, match="unsupported specialty_key"):
        _context(specialty_key="dermatology")
