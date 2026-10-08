"""Validated rule catalog view for orchestrated evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.clinical_knowledge.manifest_hash import rule_set_manifest_hash
from app.domain.clinical_decision.exceptions import ClinicalDecisionEngineUnavailableError
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog

# Re-export for existing imports.
__all__ = ["RuleCatalogView", "rule_set_manifest_hash"]


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
