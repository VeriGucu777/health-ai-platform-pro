"""Fail-closed validated filesystem clinical knowledge catalog provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.application.clinical_decision.rule_catalog_view import RuleCatalogView
from app.application.clinical_knowledge.exceptions import (
    ClinicalKnowledgeCatalogLoadError,
    ClinicalKnowledgeCatalogValidationError,
)
from app.application.clinical_knowledge.manifest_hash import rule_set_manifest_hash
from app.application.clinical_knowledge.production_rule_catalog import ValidatedProductionRuleCatalog
from app.application.clinical_knowledge.rule_catalog_validator import DefaultRuleCatalogValidator
from app.domain.clinical_knowledge.interfaces.source_registry import ClinicalKnowledgeSourceRegistry
from app.infrastructure.clinical_knowledge.filesystem_catalog import (
    ClinicalKnowledgeLoadError,
    FilesystemClinicalKnowledgeSourceRegistry,
    load_rules_from_root,
    load_sources_from_root,
)
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root


@dataclass(frozen=True)
class ValidatedClinicalKnowledgeCatalogSnapshot:
    """Immutable validated catalog session for orchestrator wiring (not prod-wired yet)."""

    knowledge_root: Path
    source_registry: ClinicalKnowledgeSourceRegistry
    rule_catalog: ValidatedProductionRuleCatalog
    loaded_source_ids: tuple[str, ...]
    loaded_rule_ids: tuple[str, ...]
    active_production_rule_ids: tuple[str, ...]
    reference_at: datetime

    def production_manifest_hash(self, specialty_key: str) -> str:
        active = self.rule_catalog.list_active_production_rules(specialty_key)
        return rule_set_manifest_hash(active)

    def rule_catalog_view(self, specialty_key: str) -> RuleCatalogView:
        return RuleCatalogView(
            catalog=self.rule_catalog,
            manifest_hash=self.production_manifest_hash(specialty_key),
            available=True,
        )


class ValidatedFilesystemClinicalRuleCatalogProvider:
    """Load, validate, and expose a read-only production rule catalog view."""

    @staticmethod
    def load(
        knowledge_root: Path | None = None,
        *,
        reference_at: datetime | None = None,
    ) -> ValidatedClinicalKnowledgeCatalogSnapshot:
        root = (knowledge_root or repository_clinical_knowledge_root()).resolve()
        if not root.is_dir():
            raise ClinicalKnowledgeCatalogLoadError(f"clinical knowledge root not found: {root}")

        validation = DefaultRuleCatalogValidator().validate_catalog(root)
        if not validation.ok:
            issues = tuple(f"{issue.code}: {issue.message}" for issue in validation.issues)
            raise ClinicalKnowledgeCatalogValidationError(
                "clinical knowledge catalog validation failed",
                issues=issues,
            )

        try:
            sources = load_sources_from_root(root)
            rules = load_rules_from_root(root)
        except ClinicalKnowledgeLoadError as exc:
            raise ClinicalKnowledgeCatalogLoadError(str(exc)) from exc

        ref = reference_at if reference_at is not None else datetime.now(UTC)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)

        source_registry = FilesystemClinicalKnowledgeSourceRegistry(sources)
        rule_catalog = ValidatedProductionRuleCatalog(
            rules,
            sources,
            reference_at=ref,
        )
        return ValidatedClinicalKnowledgeCatalogSnapshot(
            knowledge_root=root,
            source_registry=source_registry,
            rule_catalog=rule_catalog,
            loaded_source_ids=tuple(s.source_id for s in source_registry.list_sources()),
            loaded_rule_ids=tuple(sorted(r.rule_id for r in rules)),
            active_production_rule_ids=rule_catalog.active_production_rule_ids(),
            reference_at=ref,
        )
