"""Real repository clinical_knowledge catalog wired to ClinicalDecisionOrchestrator (Phase 0B.5)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.application.clinical_decision.clinical_decision_orchestrator import ClinicalDecisionOrchestrator
from app.application.clinical_decision.default_registry import build_default_specialty_registry
from app.application.clinical_decision.rule_catalog_view import RuleCatalogView
from app.application.clinical_knowledge.exceptions import ClinicalKnowledgeCatalogValidationError
from app.application.clinical_knowledge.manifest_hash import EMPTY_PRODUCTION_MANIFEST_PAYLOAD as CK_EMPTY_PAYLOAD
from app.domain.clinical_decision.constants import (
    CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION,
    CLINICAL_DECISION_ORCHESTRATOR_VERSION,
    POLICY_PROFILE_ID_NONE,
    POLICY_PROFILE_VERSION_NONE,
)
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.clinical_decision.exceptions import ClinicalDecisionEngineUnavailableError
from app.domain.clinical_decision.interfaces.policy_profile_resolver import PolicyProfileSnapshot
from app.domain.clinical_decision.models import EncounterEvaluationContext, PatientDemographicsInput
from app.infrastructure.clinical_knowledge.validated_catalog_provider import (
    ValidatedFilesystemClinicalRuleCatalogProvider,
)

_REFERENCE_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
_EXPECTED_EMPTY_PROD_HASH = hashlib.sha256(CK_EMPTY_PAYLOAD.encode("utf-8")).hexdigest()
assert _EXPECTED_EMPTY_PROD_HASH == (
    "db2c9b5ef09c12311550b37ffb84449dfb1d2f1248dd7019d2a580cb707a33b0"
), "empty production manifest hash sentinel changed; investigate before updating test"


class _FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now_utc(self) -> datetime:
        return self._moment


class _FixedEvaluationIds:
    def __init__(self, evaluation_id: UUID) -> None:
        self._evaluation_id = evaluation_id

    def new_evaluation_id(self) -> UUID:
        return self._evaluation_id


def _cardiology_context() -> EncounterEvaluationContext:
    return EncounterEvaluationContext(
        encounter_id=UUID("44444444-4444-4444-8444-444444444444"),
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        locale="en",
        patient_demographics=PatientDemographicsInput(age_years=55),
        context_version="encounter_eval_context_v1",
        created_at=datetime(2026, 1, 15, tzinfo=UTC),
    )


def _load_real_catalog_snapshot():
    return ValidatedFilesystemClinicalRuleCatalogProvider.load(reference_at=_REFERENCE_AT)


def test_real_repo_catalog_orchestrator_no_applicable_rules() -> None:
    snapshot = _load_real_catalog_snapshot()
    assert "guideline:esc:htn:2024" in snapshot.loaded_source_ids
    assert snapshot.loaded_source_ids == ("guideline:esc:htn:2024",)
    assert snapshot.loaded_rule_ids == ()
    assert snapshot.active_production_rule_ids == ()

    manifest_hash = snapshot.production_manifest_hash("cardiology")
    assert manifest_hash == _EXPECTED_EMPTY_PROD_HASH

    view = snapshot.rule_catalog_view("cardiology")
    assert view.available is True
    assert view.manifest_hash == manifest_hash
    assert view.catalog.list_active_production_rules("cardiology") == ()
    assert snapshot.rule_catalog.list_approved_demo_rules("cardiology") == ()

    fixed_time = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
    fixed_id = UUID("55555555-5555-4555-8555-555555555555")
    orchestrator = ClinicalDecisionOrchestrator(
        specialty_registry=build_default_specialty_registry(),
        rule_catalog_view=view,
        policy_profile=PolicyProfileSnapshot(
            profile_id="tr-cardiology-pilot-v1",
            profile_version="0.0.0",
            is_production_active=False,
        ),
        clock=_FixedClock(fixed_time),
        evaluation_id_factory=_FixedEvaluationIds(fixed_id),
    )

    result = orchestrator.evaluate(_cardiology_context())

    assert result.evaluation_status == EvaluationStatus.NO_APPLICABLE_RULES
    assert result.engine_version == CLINICAL_DECISION_ORCHESTRATOR_VERSION
    assert result.specialty_module_version == CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION
    assert result.rule_set_manifest_hash == manifest_hash
    assert result.policy_profile_id == POLICY_PROFILE_ID_NONE
    assert result.policy_profile_version == POLICY_PROFILE_VERSION_NONE
    assert result.differential_candidates == ()
    assert result.suggested_questions == ()
    assert result.missing_information == ()
    assert result.safety_alerts == ()
    assert result.evaluation_id == fixed_id
    assert result.evaluated_at == fixed_time


def test_invalid_catalog_load_fail_closed_before_orchestrator(tmp_path: Path) -> None:
    broken_root = tmp_path / "not_a_catalog"
    broken_root.mkdir()
    with pytest.raises(ClinicalKnowledgeCatalogValidationError):
        ValidatedFilesystemClinicalRuleCatalogProvider.load(
            broken_root,
            reference_at=_REFERENCE_AT,
        )


def test_unavailable_rule_catalog_view_does_not_silent_empty_result() -> None:
    snapshot = _load_real_catalog_snapshot()
    view = RuleCatalogView(
        catalog=snapshot.rule_catalog,
        manifest_hash=snapshot.production_manifest_hash("cardiology"),
        available=False,
    )
    orchestrator = ClinicalDecisionOrchestrator(
        specialty_registry=build_default_specialty_registry(),
        rule_catalog_view=view,
    )
    with pytest.raises(ClinicalDecisionEngineUnavailableError):
        orchestrator.evaluate(_cardiology_context())
