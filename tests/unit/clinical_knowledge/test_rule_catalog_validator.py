"""Clinical knowledge catalog validation tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.application.clinical_knowledge.rule_catalog_validator import DefaultRuleCatalogValidator
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMAS = _REPO_ROOT / "clinical_knowledge" / "schemas"


def _write_minimal_catalog(
    tmp_path: Path,
    *,
    sources: dict[str, str] | None = None,
    rules: dict[str, str] | None = None,
    profiles: dict[str, str] | None = None,
) -> Path:
    shutil.copytree(_SCHEMAS, tmp_path / "schemas")
    (tmp_path / "sources").mkdir()
    (tmp_path / "rules" / "cardiology").mkdir(parents=True)
    (tmp_path / "policy_profiles").mkdir()
    for name, body in (sources or {}).items():
        (tmp_path / "sources" / name).write_text(body, encoding="utf-8")
    for rel, body in (rules or {}).items():
        path = tmp_path / "rules" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    for name, body in (profiles or {}).items():
        (tmp_path / "policy_profiles" / name).write_text(body, encoding="utf-8")
    return tmp_path


ESC_SOURCE_YAML = """\
source_id: guideline:esc:htn:2024
source_type: guideline
title: 2024 ESC Guidelines for Elevated Blood Pressure and Hypertension
publisher_or_organization: European Society of Cardiology
edition_or_version: "2024"
publication_year: 2024
official_url: https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/elevated-blood-pressure-and-hypertension
jurisdiction:
  - EU
specialty:
  - cardiology
topic_tags:
  - hypertension
license_status: unknown
ai_usage_status: unknown
commercial_usage_status: unknown
content_ingestion_allowed: false
citation_required: true
clinical_review_status: not_reviewed
"""

DRAFT_RULE_YAML = """\
rule_id: TEST-RULE-001
specialty_key: cardiology
topic_key: hypertension
rule_type: next_best_question
status: draft
rule_version: "1.0.0"
clinical_intent: Test fixture only; no clinical meaning.
input_requirements: []
trigger_conditions: {}
exclusion_conditions: {}
output_definition:
  question_key: copilot.test.question
severity: info
priority: 10
explanation_key: copilot.test.explanation
rationale_key: copilot.test.rationale
source_refs:
  - guideline:esc:htn:2024
guideline_refs:
  - source_id: guideline:esc:htn:2024
    section_ref: test-section
evidence_refs: []
clinical_review_status: not_reviewed
"""

EMPTY_PROFILE_YAML = """\
profile_id: tr-cardiology-pilot-v1
profile_status: draft
jurisdiction: TR
specialty_key: cardiology
preferred_guideline_families:
  - esc
rule_set_version: "0.0.0"
conflict_strategy: advisor_curated_only
"""


def test_repository_catalog_passes_validation() -> None:
    result = DefaultRuleCatalogValidator().validate_catalog(repository_clinical_knowledge_root())
    assert result.ok, [issue.message for issue in result.issues]


def test_valid_metadata_source_and_draft_rule_pass(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": DRAFT_RULE_YAML},
        profiles={"tr.yaml": EMPTY_PROFILE_YAML},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert result.ok


def test_fail_duplicate_source_id(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"a.yaml": ESC_SOURCE_YAML, "b.yaml": ESC_SOURCE_YAML},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "source_load_failed" for issue in result.issues)


def test_fail_unknown_source_ref(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("guideline:esc:htn:2024", "guideline:missing:2024")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": rule},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "unknown_source_ref" for issue in result.issues)


def test_fail_ingestion_with_unknown_license(tmp_path: Path) -> None:
    bad = ESC_SOURCE_YAML.replace("content_ingestion_allowed: false", "content_ingestion_allowed: true")
    root = _write_minimal_catalog(tmp_path, sources={"esc.yaml": bad})
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok


def test_fail_ai_prohibited_with_ingestion(tmp_path: Path) -> None:
    body = ESC_SOURCE_YAML.replace("ai_usage_status: unknown", "ai_usage_status: prohibited")
    body = body.replace("content_ingestion_allowed: false", "content_ingestion_allowed: true")
    body = body.replace("license_status: unknown", "license_status: verified_open")
    root = _write_minimal_catalog(tmp_path, sources={"esc.yaml": body})
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok


def test_fail_invalid_semver(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace('rule_version: "1.0.0"', 'rule_version: "not-semver"')
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": rule},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "rule_load_failed" for issue in result.issues)


def test_fail_invalid_effective_dates(tmp_path: Path) -> None:
    rule = (
        DRAFT_RULE_YAML
        + '\neffective_from: "2026-01-02T00:00:00Z"\n'
        + 'effective_until: "2026-01-01T00:00:00Z"\n'
    )
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": rule},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "invalid_effective_dates" for issue in result.issues)


def test_fail_approved_prod_without_clinical_approval(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("status: draft", "status: approved_prod")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": rule},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "prod_missing_clinical_review" for issue in result.issues)
    assert any(issue.code == "prod_missing_approval_metadata" for issue in result.issues)


def test_fail_approved_prod_with_unknown_source_license(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("status: draft", "status: approved_prod")
    rule += """
clinical_review_status: approved
reviewed_by: clinician-a
reviewed_at: "2026-01-01T12:00:00Z"
approved_by: clinician-b
approved_at: "2026-01-02T12:00:00Z"
"""
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/test.yaml": rule},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "prod_unverified_source_license" for issue in result.issues)


def test_fail_duplicate_rule_id(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={
            "cardiology/a.yaml": DRAFT_RULE_YAML,
            "cardiology/b.yaml": DRAFT_RULE_YAML,
        },
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "rule_load_failed" for issue in result.issues)


def test_fail_circular_supersedes(tmp_path: Path) -> None:
    rule_a = DRAFT_RULE_YAML.replace("TEST-RULE-001", "TEST-RULE-A")
    rule_a += "\nsupersedes_rule_id: TEST-RULE-B\n"
    rule_b = DRAFT_RULE_YAML.replace("TEST-RULE-001", "TEST-RULE-B")
    rule_b += "\nsupersedes_rule_id: TEST-RULE-A\n"
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/a.yaml": rule_a, "cardiology/b.yaml": rule_b},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok
    assert any(issue.code == "circular_supersedes" for issue in result.issues)


def test_filesystem_registry_loads_esc_source() -> None:
    from app.infrastructure.clinical_knowledge.filesystem_catalog import (
        FilesystemClinicalKnowledgeSourceRegistry,
    )

    registry = FilesystemClinicalKnowledgeSourceRegistry.from_knowledge_root(
        repository_clinical_knowledge_root(),
    )
    source = registry.get_source("guideline:esc:htn:2024")
    assert source is not None
    assert source.content_ingestion_allowed is False

    from app.infrastructure.clinical_knowledge.filesystem_catalog import FilesystemClinicalRuleCatalog

    catalog = FilesystemClinicalRuleCatalog.from_knowledge_root(repository_clinical_knowledge_root())
    assert catalog.list_active_production_rules("cardiology") == ()


def test_safe_source_id_rejects_traversal() -> None:
    from app.infrastructure.clinical_knowledge.paths import assert_safe_source_id

    with pytest.raises(ValueError):
        assert_safe_source_id("../etc/passwd")
