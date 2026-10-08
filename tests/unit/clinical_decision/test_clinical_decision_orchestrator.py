"""Clinical decision orchestrator tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.clinical_decision.clinical_decision_orchestrator import ClinicalDecisionOrchestrator
from app.application.clinical_decision.default_registry import build_default_specialty_registry
from app.application.clinical_decision.rule_catalog_view import RuleCatalogView
from app.application.clinical_decision.specialty_registry import SpecialtyDecisionModuleRegistry
from app.domain.clinical_decision.constants import (
    CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION,
    CLINICAL_DECISION_ORCHESTRATOR_VERSION,
    POLICY_PROFILE_ID_NONE,
    POLICY_PROFILE_VERSION_NONE,
)
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.clinical_decision.exceptions import (
    ClinicalDecisionEngineUnavailableError,
    UnsupportedSpecialtyError,
)
from app.domain.clinical_decision.interfaces.policy_profile_resolver import PolicyProfileSnapshot
from app.domain.clinical_decision.models import EncounterEvaluationContext, PatientDemographicsInput
from app.infrastructure.clinical_knowledge.filesystem_catalog import FilesystemClinicalRuleCatalog
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root
from tests.support.memory_clinical_rule_catalog import MemoryClinicalRuleCatalog, UnavailableClinicalRuleCatalog


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


def _context() -> EncounterEvaluationContext:
    encounter_id = UUID("22222222-2222-4222-8222-222222222222")
    return EncounterEvaluationContext(
        encounter_id=encounter_id,
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        locale="en",
        patient_demographics=PatientDemographicsInput(age_years=60),
        context_version="encounter_eval_context_v1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _orchestrator(
    *,
    registry: SpecialtyDecisionModuleRegistry | None = None,
    catalog: MemoryClinicalRuleCatalog | None = None,
    available: bool = True,
    policy: PolicyProfileSnapshot | None = None,
) -> ClinicalDecisionOrchestrator:
    reg = registry or build_default_specialty_registry()
    cat = catalog or MemoryClinicalRuleCatalog()
    view = RuleCatalogView.from_catalog(cat, specialty_key="cardiology", available=available)
    fixed_time = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
    fixed_id = UUID("33333333-3333-4333-8333-333333333333")
    return ClinicalDecisionOrchestrator(
        specialty_registry=reg,
        rule_catalog_view=view,
        policy_profile=policy,
        clock=FixedClock(fixed_time),
        evaluation_id_factory=FixedEvaluationIds(fixed_id),
    )


def test_orchestrator_cardiology_empty_catalog_no_applicable_rules() -> None:
    engine = _orchestrator()
    result = engine.evaluate(_context())
    assert result.evaluation_status == EvaluationStatus.NO_APPLICABLE_RULES
    assert result.differential_candidates == ()
    assert result.suggested_questions == ()
    assert result.missing_information == ()
    assert result.safety_alerts == ()
    assert result.engine_version == CLINICAL_DECISION_ORCHESTRATOR_VERSION
    assert result.specialty_module_version == CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION
    assert result.encounter_id == _context().encounter_id
    assert len(result.rule_set_manifest_hash) == 64


def test_orchestrator_deterministic_semantic_output() -> None:
    engine = _orchestrator()
    first = engine.evaluate(_context())
    second = engine.evaluate(_context())
    assert first == second


def test_orchestrator_unsupported_specialty() -> None:
    empty_registry = SpecialtyDecisionModuleRegistry()
    engine = _orchestrator(registry=empty_registry)
    with pytest.raises(UnsupportedSpecialtyError):
        engine.evaluate(_context())


def test_orchestrator_catalog_unavailable() -> None:
    view = RuleCatalogView(
        catalog=UnavailableClinicalRuleCatalog(),
        manifest_hash="unavailable",
        available=False,
    )
    engine = ClinicalDecisionOrchestrator(
        specialty_registry=build_default_specialty_registry(),
        rule_catalog_view=view,
    )
    with pytest.raises(ClinicalDecisionEngineUnavailableError):
        engine.evaluate(_context())


def test_draft_policy_profile_not_presented_as_production() -> None:
    draft_policy = PolicyProfileSnapshot(
        profile_id="tr-cardiology-pilot-v1",
        profile_version="0.0.0",
        is_production_active=False,
    )
    engine = _orchestrator(policy=draft_policy)
    result = engine.evaluate(_context())
    assert result.policy_profile_id == POLICY_PROFILE_ID_NONE
    assert result.policy_profile_version == POLICY_PROFILE_VERSION_NONE


def test_filesystem_catalog_has_zero_active_production_rules() -> None:
    catalog = FilesystemClinicalRuleCatalog.from_knowledge_root(
        repository_clinical_knowledge_root(),
    )
    assert catalog.list_active_production_rules("cardiology") == ()
