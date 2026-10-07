"""Port for read-only clinical rule catalog."""

from abc import ABC, abstractmethod

from app.domain.clinical_knowledge.enums import ClinicalRuleStatus
from app.domain.clinical_knowledge.models import ClinicalRule


class ClinicalRuleCatalog(ABC):
    """Load validated clinical rules from a versioned catalog."""

    @abstractmethod
    def list_rules(
        self,
        *,
        specialty_key: str | None = None,
        status: ClinicalRuleStatus | None = None,
    ) -> tuple[ClinicalRule, ...]:
        """Return rules filtered by specialty and/or lifecycle status."""

    @abstractmethod
    def get_rule(self, rule_id: str) -> ClinicalRule | None:
        """Return one rule by stable identifier."""

    @abstractmethod
    def list_active_production_rules(self, specialty_key: str) -> tuple[ClinicalRule, ...]:
        """Return approved_prod rules for a specialty (empty in Phase 0B.1)."""
