"""No-op clinical decision engine — zero clinical claims until rules are approved."""

from uuid import UUID

from app.application.clinical_decision.time_ports import (
    ClockPort,
    EvaluationIdFactoryPort,
    SystemUtcClock,
    UuidEvaluationIdFactory,
)
from app.domain.clinical_decision.constants import (
    NOOP_ENGINE_VERSION,
    POLICY_PROFILE_ID_NONE,
    POLICY_PROFILE_VERSION_NONE,
    RULE_SET_MANIFEST_HASH_EMPTY,
    SPECIALTY_MODULE_VERSION_NONE,
)
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.clinical_decision.interfaces.clinical_decision_engine import ClinicalDecisionEnginePort
from app.domain.clinical_decision.models import (
    ClinicalDecisionEvaluationResult,
    EncounterEvaluationContext,
)


class NoOpClinicalDecisionEngine(ClinicalDecisionEnginePort):
    """Deterministic engine skeleton with no rule catalog dependency."""

    def __init__(
        self,
        *,
        clock: ClockPort | None = None,
        evaluation_id_factory: EvaluationIdFactoryPort | None = None,
    ) -> None:
        self._clock = clock or SystemUtcClock()
        self._evaluation_ids = evaluation_id_factory or UuidEvaluationIdFactory()

    @property
    def engine_version(self) -> str:
        return NOOP_ENGINE_VERSION

    @property
    def specialty_module_version(self) -> str:
        return SPECIALTY_MODULE_VERSION_NONE

    def evaluate(self, context: EncounterEvaluationContext) -> ClinicalDecisionEvaluationResult:
        evaluated_at = self._clock.now_utc()
        return ClinicalDecisionEvaluationResult(
            evaluation_id=self._evaluation_ids.new_evaluation_id(),
            encounter_id=context.encounter_id,
            engine_version=self.engine_version,
            specialty_module_version=self.specialty_module_version,
            policy_profile_id=POLICY_PROFILE_ID_NONE,
            policy_profile_version=POLICY_PROFILE_VERSION_NONE,
            rule_set_manifest_hash=RULE_SET_MANIFEST_HASH_EMPTY,
            evaluated_at=evaluated_at,
            evaluation_status=EvaluationStatus.NO_APPLICABLE_RULES,
            differential_candidates=(),
            suggested_questions=(),
            missing_information=(),
            safety_alerts=(),
        )
