"""Read-only filesystem clinical knowledge registry and rule catalog."""

from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from app.application.clinical_knowledge.license_gates import validate_source_license_invariants
from app.domain.clinical_knowledge.enums import ClinicalRuleStatus
from app.domain.clinical_knowledge.interfaces.rule_catalog import ClinicalRuleCatalog
from app.domain.clinical_knowledge.interfaces.source_registry import ClinicalKnowledgeSourceRegistry
from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource, ClinicalRule
from app.infrastructure.clinical_knowledge.mapping import rule_from_dict, source_from_dict
from app.infrastructure.clinical_knowledge.paths import assert_safe_rule_id, assert_safe_source_id
from app.application.clinical_knowledge.exceptions import ClinicalKnowledgeCatalogIntegrityError
from app.infrastructure.clinical_knowledge.yaml_loader import (
    iter_manifest_yaml_files,
    iter_manifest_yaml_files_recursive,
    load_yaml_mapping,
)


class ClinicalKnowledgeLoadError(Exception):
    """Raised when manifests fail structural validation at load time."""


def _schema_validator(schema_path: Path) -> Draft202012Validator:
    import json

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _validate_against_schema(
    data: dict[str, object],
    validator: Draft202012Validator,
    *,
    manifest_path: Path,
) -> None:
    errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        raise ClinicalKnowledgeLoadError(
            f"{manifest_path}: schema violation at {location}: {first.message}",
        )


def load_sources_from_root(knowledge_root: Path) -> tuple[ClinicalKnowledgeSource, ...]:
    """Load and validate all source manifests (fail closed)."""
    root = knowledge_root.resolve()
    schema_path = root / "schemas" / "clinical_knowledge_source.schema.json"
    validator = _schema_validator(schema_path)
    sources_dir = root / "sources"
    seen: set[str] = set()
    loaded: list[ClinicalKnowledgeSource] = []

    for path in iter_manifest_yaml_files(sources_dir):
        try:
            data = load_yaml_mapping(path, knowledge_root=root)
        except (ValueError, ClinicalKnowledgeCatalogIntegrityError) as exc:
            raise ClinicalKnowledgeLoadError(str(exc)) from exc
        _validate_against_schema(data, validator, manifest_path=path)
        source = source_from_dict(data)
        assert_safe_source_id(source.source_id)
        if source.source_id in seen:
            raise ClinicalKnowledgeLoadError(f"duplicate source_id {source.source_id!r} in {path}")
        seen.add(source.source_id)
        license_issues = validate_source_license_invariants(source)
        if license_issues:
            raise ClinicalKnowledgeLoadError(
                f"{path}: license invariant failed: {'; '.join(license_issues)}",
            )
        loaded.append(source)

    return tuple(loaded)


def load_rules_from_root(knowledge_root: Path) -> tuple[ClinicalRule, ...]:
    """Load and validate all rule YAML files under rules/ (fail closed)."""
    root = knowledge_root.resolve()
    schema_path = root / "schemas" / "clinical_rule.schema.json"
    validator = _schema_validator(schema_path)
    rules_dir = root / "rules"
    seen: set[str] = set()
    loaded: list[ClinicalRule] = []

    if not rules_dir.is_dir():
        return ()

    for path in iter_manifest_yaml_files_recursive(rules_dir):
        try:
            data = load_yaml_mapping(path, knowledge_root=root)
        except (ValueError, ClinicalKnowledgeCatalogIntegrityError) as exc:
            raise ClinicalKnowledgeLoadError(str(exc)) from exc
        _validate_against_schema(data, validator, manifest_path=path)
        rule = rule_from_dict(data)
        assert_safe_rule_id(rule.rule_id)
        if rule.rule_id in seen:
            raise ClinicalKnowledgeLoadError(f"duplicate rule_id {rule.rule_id!r} in {path}")
        seen.add(rule.rule_id)
        loaded.append(rule)

    return tuple(loaded)


class FilesystemClinicalKnowledgeSourceRegistry(ClinicalKnowledgeSourceRegistry):
    """In-memory registry loaded once from disk (read-only)."""

    def __init__(self, sources: tuple[ClinicalKnowledgeSource, ...]) -> None:
        self._by_id = {source.source_id: source for source in sources}

    @classmethod
    def from_knowledge_root(cls, knowledge_root: Path) -> FilesystemClinicalKnowledgeSourceRegistry:
        return cls(load_sources_from_root(knowledge_root))

    def get_source(self, source_id: str) -> ClinicalKnowledgeSource | None:
        assert_safe_source_id(source_id)
        return self._by_id.get(source_id)

    def list_sources(self) -> tuple[ClinicalKnowledgeSource, ...]:
        return tuple(sorted(self._by_id.values(), key=lambda s: s.source_id))

    def exists(self, source_id: str) -> bool:
        assert_safe_source_id(source_id)
        return source_id in self._by_id


class FilesystemClinicalRuleCatalog(ClinicalRuleCatalog):
    """In-memory rule catalog loaded from disk (read-only)."""

    def __init__(self, rules: tuple[ClinicalRule, ...]) -> None:
        self._rules = rules
        self._by_id = {rule.rule_id: rule for rule in rules}

    @classmethod
    def from_knowledge_root(cls, knowledge_root: Path) -> FilesystemClinicalRuleCatalog:
        return cls(load_rules_from_root(knowledge_root))

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
        assert_safe_rule_id(rule_id)
        return self._by_id.get(rule_id)

    def list_active_production_rules(self, specialty_key: str) -> tuple[ClinicalRule, ...]:
        return self.list_rules(
            specialty_key=specialty_key,
            status=ClinicalRuleStatus.APPROVED_PROD,
        )
