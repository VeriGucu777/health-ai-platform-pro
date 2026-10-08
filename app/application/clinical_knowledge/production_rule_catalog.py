"""Read-only rule catalog exposing production-active rules only."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.clinical_knowledge.production_rules import is_production_eligible_rule
from app.domain.clinical_knowledge.enums import ClinicalRuleStatus
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog
from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource, ClinicalRule


class ValidatedProductionRuleCatalog(ClinicalRuleCatalog):
    """Immutable validated catalog; production lists apply strict eligibility filters."""

    def __init__(
        self,
        rules: tuple[ClinicalRule, ...],
        sources: tuple[ClinicalKnowledgeSource, ...],
        *,
        reference_at: datetime,
    ) -> None:
        self._rules = tuple(rules)
        self._by_id = {rule.rule_id: rule for rule in self._rules}
        self._sources_by_id = {source.source_id: source for source in sources}
        self._reference_at = reference_at if reference_at.tzinfo else reference_at.replace(tzinfo=UTC)

    @property
    def reference_at(self) -> datetime:
        return self._reference_at

    @property
    def all_rules(self) -> tuple[ClinicalRule, ...]:
        return self._rules

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
        eligible = [
            rule
            for rule in self._rules
            if rule.specialty_key == specialty_key
            and is_production_eligible_rule(
                rule,
                reference_at=self._reference_at,
                sources_by_id=self._sources_by_id,
            )
        ]
        return tuple(sorted(eligible, key=lambda r: r.rule_id))

    def list_approved_demo_rules(self, specialty_key: str) -> tuple[ClinicalRule, ...]:
        return self.list_rules(
            specialty_key=specialty_key,
            status=ClinicalRuleStatus.APPROVED_DEMO,
        )

    def active_production_rule_ids(self) -> tuple[str, ...]:
        keys = {
            rule.rule_id
            for rule in self._rules
            if is_production_eligible_rule(
                rule,
                reference_at=self._reference_at,
                sources_by_id=self._sources_by_id,
            )
        }
        return tuple(sorted(keys))
