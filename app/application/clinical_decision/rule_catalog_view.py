"""Validated rule catalog view for orchestrated evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.domain.clinical_decision.exceptions import ClinicalDecisionEngineUnavailableError
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog
from app.domain.clinical_knowledge.models import ClinicalRule


def rule_set_manifest_hash(rules: tuple[ClinicalRule, ...]) -> str:
    """Deterministic identity for an approved-production rule set (empty set included)."""
    if not rules:
        payload = "approved_prod_rules:v1:empty"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    parts = sorted(f"{rule.rule_id}:{rule.rule_version}" for rule in rules)
    payload = "approved_prod_rules:v1:" + "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RuleCatalogView:
    """Read-only catalog session with availability and manifest identity."""

    catalog: ClinicalRuleCatalog
    manifest_hash: str
    available: bool = True

    @classmethod
    def from_catalog(
        cls,
        catalog: ClinicalRuleCatalog,
        *,
        specialty_key: str,
        available: bool = True,
    ) -> RuleCatalogView:
        active = catalog.list_active_production_rules(specialty_key)
        return cls(
            catalog=catalog,
            manifest_hash=rule_set_manifest_hash(active),
            available=available,
        )

    def require_available(self) -> ClinicalRuleCatalog:
        if not self.available:
            raise ClinicalDecisionEngineUnavailableError("Clinical rule catalog is unavailable")
        return self.catalog
