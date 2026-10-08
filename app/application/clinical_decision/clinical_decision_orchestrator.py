"""Orchestrates specialty modules and validated rule catalogs into evaluation results."""

from app.application.clinical_decision.rule_catalog_view import RuleCatalogView
from app.application.clinical_decision.time_ports import (
    ClockPort,
    EvaluationIdFactoryPort,
    SystemUtcClock,
    UuidEvaluationIdFactory,
)
from app.domain.clinical_decision.constants import (
    CLINICAL_DECISION_ORCHESTRATOR_VERSION,
    POLICY_PROFILE_ID_NONE,
    POLICY_PROFILE_VERSION_NONE,
    SPECIALTY_MODULE_VERSION_NONE,
)
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.clinical_decision.interfaces.clinical_decision_engine import ClinicalDecisionEnginePort
from app.domain.clinical_decision.interfaces.policy_profile_resolver import PolicyProfileSnapshot
from app.domain.clinical_decision.interfaces.specialty_module_registry import SpecialtyDecisionModuleRegistryPort
from app.domain.clinical_decision.models import (
    ClinicalDecisionEvaluationResult,
    EncounterEvaluationContext,
)


class ClinicalDecisionOrchestrator(ClinicalDecisionEnginePort):
    """Resolve specialty module + rule catalog; no clinical scoring in orchestrator."""

    def __init__(
        self,
        *,
        specialty_registry: SpecialtyDecisionModuleRegistryPort,
        rule_catalog_view: RuleCatalogView,
        policy_profile: PolicyProfileSnapshot | None = None,
        clock: ClockPort | None = None,
        evaluation_id_factory: EvaluationIdFactoryPort | None = None,
    ) -> None:
        self._registry = specialty_registry
        self._catalog_view = rule_catalog_view
        self._policy = policy_profile or PolicyProfileSnapshot(
            profile_id=POLICY_PROFILE_ID_NONE,
            profile_version=POLICY_PROFILE_VERSION_NONE,
            is_production_active=False,
        )
        self._clock = clock or SystemUtcClock()
        self._evaluation_ids = evaluation_id_factory or UuidEvaluationIdFactory()
        self._last_specialty_module_version = SPECIALTY_MODULE_VERSION_NONE

    @property
    def engine_version(self) -> str:
        return CLINICAL_DECISION_ORCHESTRATOR_VERSION

    @property
    def specialty_module_version(self) -> str:
        return self._last_specialty_module_version

    def evaluate(self, context: EncounterEvaluationContext) -> ClinicalDecisionEvaluationResult:
        module = self._registry.resolve(context.specialty_key)
        self._last_specialty_module_version = module.module_version

        catalog = self._catalog_view.require_available()
        slice_result = module.evaluate(context, catalog)

        active_rules = catalog.list_active_production_rules(context.specialty_key)
        has_outputs = bool(
            slice_result.differential_candidates
            or slice_result.suggested_questions
            or slice_result.missing_information
            or slice_result.safety_alerts
        )
        if active_rules and has_outputs:
            status = EvaluationStatus.SUCCESS
        else:
            status = EvaluationStatus.NO_APPLICABLE_RULES

        policy_id = self._policy.profile_id
        policy_version = self._policy.profile_version
        if not self._policy.is_production_active:
            policy_id = POLICY_PROFILE_ID_NONE
            policy_version = POLICY_PROFILE_VERSION_NONE

        evaluated_at = self._clock.now_utc()
        return ClinicalDecisionEvaluationResult(
            evaluation_id=self._evaluation_ids.new_evaluation_id(),
            encounter_id=context.encounter_id,
            engine_version=self.engine_version,
            specialty_module_version=module.module_version,
            policy_profile_id=policy_id,
            policy_profile_version=policy_version,
            rule_set_manifest_hash=self._catalog_view.manifest_hash,
            evaluated_at=evaluated_at,
            evaluation_status=status,
            differential_candidates=slice_result.differential_candidates,
            suggested_questions=slice_result.suggested_questions,
            missing_information=slice_result.missing_information,
            safety_alerts=slice_result.safety_alerts,
        )
