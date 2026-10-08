"""Full clinical knowledge catalog validation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from app.application.clinical_knowledge.license_gates import validate_source_license_invariants
from app.domain.clinical_knowledge.enums import (
    KNOWN_SPECIALTY_KEYS,
    LICENSE_STATUSES_ACCEPTABLE_FOR_PROD_RULE_CITATION,
    ClinicalKnowledgeReviewStatus,
    ClinicalRuleStatus,
    ClinicalRuleType,
)
from app.domain.clinical_knowledge.interfaces.rule_validator import (
    RuleCatalogValidationIssue,
    RuleCatalogValidationResult,
    RuleCatalogValidator,
)
from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource, ClinicalRule
from app.infrastructure.clinical_knowledge.filesystem_catalog import (
    ClinicalKnowledgeLoadError,
    load_rules_from_root,
    load_sources_from_root,
)
from app.infrastructure.clinical_knowledge.mapping import policy_profile_from_dict
from app.infrastructure.clinical_knowledge.paths import assert_safe_source_id
from app.infrastructure.clinical_knowledge.yaml_loader import iter_manifest_yaml_files, load_yaml_mapping


def _schema_validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _parse_effective_bounds(rule: ClinicalRule) -> tuple[datetime | None, datetime | None]:
    start = rule.effective_from
    end = rule.effective_until
    if start is not None and end is not None and start > end:
        raise ValueError("effective_from after effective_until")
    return start, end


class DefaultRuleCatalogValidator(RuleCatalogValidator):
    """Validate schemas, references, license gates, and lifecycle constraints."""

    def validate_catalog(self, knowledge_root: Path) -> RuleCatalogValidationResult:
        result = RuleCatalogValidationResult()
        root = knowledge_root.resolve()

        if not root.is_dir():
            result.issues.append(
                RuleCatalogValidationIssue(
                    code="missing_root",
                    message=f"knowledge root not found: {root}",
                ),
            )
            return result

        for schema_name in (
            "clinical_knowledge_source.schema.json",
            "clinical_rule.schema.json",
            "clinical_policy_profile.schema.json",
        ):
            schema_path = root / "schemas" / schema_name
            if not schema_path.is_file():
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="missing_schema",
                        message=f"missing schema file: {schema_path}",
                        path=str(schema_path),
                    ),
                )
        if result.issues:
            return result

        sources: tuple[ClinicalKnowledgeSource, ...] = ()
        rules: tuple[ClinicalRule, ...] = ()
        try:
            sources = load_sources_from_root(root)
        except ClinicalKnowledgeLoadError as exc:
            result.issues.append(
                RuleCatalogValidationIssue(code="source_load_failed", message=str(exc)),
            )
        try:
            rules = load_rules_from_root(root)
        except ClinicalKnowledgeLoadError as exc:
            result.issues.append(
                RuleCatalogValidationIssue(code="rule_load_failed", message=str(exc)),
            )
        if not result.ok:
            return result

        source_by_id = {source.source_id: source for source in sources}
        if len(source_by_id) != len(sources):
            result.issues.append(
                RuleCatalogValidationIssue(
                    code="duplicate_source_id",
                    message="duplicate source_id detected during load",
                ),
            )

        rule_by_id = {rule.rule_id: rule for rule in rules}
        if len(rule_by_id) != len(rules):
            result.issues.append(
                RuleCatalogValidationIssue(
                    code="duplicate_rule_id",
                    message="duplicate rule_id detected during load",
                ),
            )

        for source in sources:
            for msg in validate_source_license_invariants(source):
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="license_invariant",
                        message=f"{source.source_id}: {msg}",
                        path=source.source_id,
                    ),
                )
            if source.supersedes_source_id is not None:
                supersede_invalid = False
                try:
                    assert_safe_source_id(source.supersedes_source_id)
                except ValueError as exc:
                    supersede_invalid = True
                    result.issues.append(
                        RuleCatalogValidationIssue(
                            code="unsafe_supersedes_source_id",
                            message=str(exc),
                            path=source.source_id,
                        ),
                    )
                if (
                    not supersede_invalid
                    and source.supersedes_source_id not in source_by_id
                ):
                    result.issues.append(
                        RuleCatalogValidationIssue(
                            code="unknown_supersedes_source",
                            message=f"{source.source_id} supersedes unknown {source.supersedes_source_id}",
                            path=source.source_id,
                        ),
                    )

        profile_validator = _schema_validator(root / "schemas" / "clinical_policy_profile.schema.json")
        seen_profile_ids: set[str] = set()
        for path in iter_manifest_yaml_files(root / "policy_profiles"):
            try:
                data = load_yaml_mapping(path, knowledge_root=root)
            except ValueError as exc:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="profile_yaml_invalid",
                        message=str(exc),
                        path=str(path),
                    ),
                )
                continue
            schema_errors = sorted(profile_validator.iter_errors(data), key=lambda e: e.path)
            if schema_errors:
                err = schema_errors[0]
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="profile_schema_invalid",
                        message=f"{path}: {err.message}",
                        path=str(path),
                    ),
                )
                continue
            profile = policy_profile_from_dict(data)
            if profile.profile_id in seen_profile_ids:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="duplicate_profile_id",
                        message=f"duplicate profile_id {profile.profile_id!r} in {path}",
                        path=str(path),
                    ),
                )
                continue
            seen_profile_ids.add(profile.profile_id)
            if profile.specialty_key not in KNOWN_SPECIALTY_KEYS:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="unknown_specialty",
                        message=f"profile {profile.profile_id} specialty_key={profile.specialty_key!r}",
                        path=str(path),
                    ),
                )

        for rule in rules:
            if rule.specialty_key not in KNOWN_SPECIALTY_KEYS:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="unknown_specialty",
                        message=f"rule {rule.rule_id} specialty_key={rule.specialty_key!r}",
                        path=rule.rule_id,
                    ),
                )
            try:
                _parse_effective_bounds(rule)
            except ValueError as exc:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="invalid_effective_dates",
                        message=f"{rule.rule_id}: {exc}",
                        path=rule.rule_id,
                    ),
                )

            for ref in rule.source_refs:
                if ref not in source_by_id:
                    result.issues.append(
                        RuleCatalogValidationIssue(
                            code="unknown_source_ref",
                            message=f"rule {rule.rule_id} references unknown source {ref!r}",
                            path=rule.rule_id,
                        ),
                    )
            for gref in rule.guideline_refs:
                if gref.source_id not in source_by_id:
                    result.issues.append(
                        RuleCatalogValidationIssue(
                            code="unknown_guideline_source_ref",
                            message=(
                                f"rule {rule.rule_id} guideline_ref unknown source "
                                f"{gref.source_id!r}"
                            ),
                            path=rule.rule_id,
                        ),
                    )

            if rule.status == ClinicalRuleStatus.APPROVED_PROD:
                self._validate_prod_rule(rule, source_by_id, result)

        self._validate_supersedes_cycles(rules, result)

        return result

    def _validate_prod_rule(
        self,
        rule: ClinicalRule,
        source_by_id: dict[str, ClinicalKnowledgeSource],
        result: RuleCatalogValidationResult,
    ) -> None:
        if rule.clinical_review_status not in (
            ClinicalKnowledgeReviewStatus.REVIEWED,
            ClinicalKnowledgeReviewStatus.APPROVED,
        ):
            result.issues.append(
                RuleCatalogValidationIssue(
                    code="prod_missing_clinical_review",
                    message=f"rule {rule.rule_id} approved_prod requires clinical review approval",
                    path=rule.rule_id,
                ),
            )
        for field_name in ("reviewed_by", "reviewed_at", "approved_by", "approved_at"):
            if getattr(rule, field_name) is None:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="prod_missing_approval_metadata",
                        message=f"rule {rule.rule_id} approved_prod missing {field_name}",
                        path=rule.rule_id,
                    ),
                )
        for ref in rule.source_refs:
            source = source_by_id.get(ref)
            if source is None:
                continue
            if source.license_status not in LICENSE_STATUSES_ACCEPTABLE_FOR_PROD_RULE_CITATION:
                result.issues.append(
                    RuleCatalogValidationIssue(
                        code="prod_unverified_source_license",
                        message=(
                            f"rule {rule.rule_id} approved_prod cites source {ref} "
                            f"with license_status={source.license_status!s}"
                        ),
                        path=rule.rule_id,
                    ),
                )
        if rule.rule_type == ClinicalRuleType.RED_FLAG and rule.reviewed_by == rule.approved_by:
            result.issues.append(
                RuleCatalogValidationIssue(
                    code="red_flag_dual_approval",
                    message=(
                        f"rule {rule.rule_id} red_flag approved_prod requires distinct "
                        "reviewed_by and approved_by"
                    ),
                    path=rule.rule_id,
                ),
            )

    def _validate_supersedes_cycles(
        self,
        rules: tuple[ClinicalRule, ...],
        result: RuleCatalogValidationResult,
    ) -> None:
        graph: dict[str, str | None] = {
            rule.rule_id: rule.supersedes_rule_id for rule in rules if rule.supersedes_rule_id
        }
        for start in graph:
            visited: set[str] = set()
            current: str | None = start
            while current is not None:
                if current in visited:
                    result.issues.append(
                        RuleCatalogValidationIssue(
                            code="circular_supersedes",
                            message=f"circular supersedes chain involving {start}",
                            path=start,
                        ),
                    )
                    break
                visited.add(current)
                current = graph.get(current)
