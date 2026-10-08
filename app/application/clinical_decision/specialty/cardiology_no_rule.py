"""Cardiology specialty stub — consumes validated rules only; zero claims when none are active."""

from app.domain.clinical_decision.constants import CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION
from app.domain.clinical_decision.interfaces.specialty_decision_module import SpecialtyDecisionModulePort
from app.domain.clinical_decision.models import EncounterEvaluationContext, SpecialtyEvaluationSlice
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog


class CardiologyNoRuleSpecialtyModule(SpecialtyDecisionModulePort):
    """Cardiology pack placeholder until approved_prod rules exist."""

    @property
    def specialty_key(self) -> str:
        return "cardiology"

    @property
    def module_version(self) -> str:
        return CARDIOLOGY_SPECIALTY_MODULE_STUB_VERSION

    def evaluate(
        self,
        context: EncounterEvaluationContext,
        rule_catalog: ClinicalRuleCatalog,
    ) -> SpecialtyEvaluationSlice:
        if context.specialty_key != self.specialty_key:
            msg = f"cardiology module received mismatched specialty_key: {context.specialty_key!r}"
            raise ValueError(msg)

        active_rules = rule_catalog.list_active_production_rules(self.specialty_key)
        if not active_rules:
            return SpecialtyEvaluationSlice()

        # Future: execute approved_prod rules only (Phase 0B.4+).
        return SpecialtyEvaluationSlice()
