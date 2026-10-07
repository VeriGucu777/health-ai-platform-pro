"""Port for specialty-specific rule evaluation (no direct source file access)."""

from abc import ABC, abstractmethod

from app.domain.clinical_decision.models import EncounterEvaluationContext, SpecialtyEvaluationSlice
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog


class SpecialtyDecisionModulePort(ABC):
    """Run validated rules for one specialty via the rule catalog port."""

    @property
    @abstractmethod
    def specialty_key(self) -> str:
        """Specialty identifier (e.g. cardiology)."""

    @property
    @abstractmethod
    def module_version(self) -> str:
        """Specialty module semver or stable id."""

    @abstractmethod
    def evaluate(
        self,
        context: EncounterEvaluationContext,
        rule_catalog: ClinicalRuleCatalog,
    ) -> SpecialtyEvaluationSlice:
        """Return specialty slice; empty when no applicable approved rules."""
