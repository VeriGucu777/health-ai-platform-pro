"""In-memory clinical rule catalog for unit tests."""

from app.domain.clinical_knowledge.enums import ClinicalRuleStatus
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog
from app.domain.clinical_knowledge.models import ClinicalRule


class MemoryClinicalRuleCatalog(ClinicalRuleCatalog):
    """Test double; never loads filesystem YAML."""

    def __init__(self, rules: tuple[ClinicalRule, ...] = ()) -> None:
        self._rules = rules
        self._by_id = {rule.rule_id: rule for rule in rules}

    def list_rules(
        self,
        *,
        specialty_key: str | None = None,
        status: ClinicalRuleStatus | None = None,
    ) -> tuple[ClinicalRule, ...]:
        items = self._rules
        if specialty_key is not None:
            items = tuple(r for r in items if r.specialty_key == specialty_key)
        if status is not None:
            items = tuple(r for r in items if r.status == status)
        return tuple(sorted(items, key=lambda r: r.rule_id))

    def get_rule(self, rule_id: str) -> ClinicalRule | None:
        return self._by_id.get(rule_id)

    def list_active_production_rules(self, specialty_key: str) -> tuple[ClinicalRule, ...]:
        return self.list_rules(
            specialty_key=specialty_key,
            status=ClinicalRuleStatus.APPROVED_PROD,
        )


class UnavailableClinicalRuleCatalog(ClinicalRuleCatalog):
    """Simulates corrupted/unavailable catalog session."""

    def list_rules(
        self,
        *,
        specialty_key: str | None = None,
        status: ClinicalRuleStatus | None = None,
    ) -> tuple[ClinicalRule, ...]:
        raise RuntimeError("catalog corrupted")

    def get_rule(self, rule_id: str) -> ClinicalRule | None:
        raise RuntimeError("catalog corrupted")

    def list_active_production_rules(self, specialty_key: str) -> tuple[ClinicalRule, ...]:
        raise RuntimeError("catalog corrupted")
