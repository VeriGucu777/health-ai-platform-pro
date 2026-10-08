"""Validated filesystem clinical rule catalog provider (Phase 0B.4)."""

from __future__ import annotations

import ast
import hashlib
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.clinical_knowledge.exceptions import (
    ClinicalKnowledgeCatalogIntegrityError,
    ClinicalKnowledgeCatalogLoadError,
    ClinicalKnowledgeCatalogValidationError,
)
from app.application.clinical_knowledge.manifest_hash import (
    EMPTY_PRODUCTION_MANIFEST_PAYLOAD,
    rule_set_manifest_hash,
)
from app.application.clinical_knowledge.rule_catalog_validator import DefaultRuleCatalogValidator
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root
from app.infrastructure.clinical_knowledge.validated_catalog_provider import (
    ValidatedFilesystemClinicalRuleCatalogProvider,
)
from app.infrastructure.clinical_knowledge.yaml_loader import (
    ensure_manifest_path_under_root,
    load_yaml_mapping,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMAS = _REPO_ROOT / "clinical_knowledge" / "schemas"
_REF_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
_EMPTY_HASH = hashlib.sha256(EMPTY_PRODUCTION_MANIFEST_PAYLOAD.encode("utf-8")).hexdigest()


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

VERIFIED_ESC_SOURCE_YAML = ESC_SOURCE_YAML.replace(
    "license_status: unknown", "license_status: verified_open"
).replace("ai_usage_status: unknown", "ai_usage_status: allowed").replace(
    "commercial_usage_status: unknown", "commercial_usage_status: allowed"
)

DRAFT_RULE_YAML = """\
rule_id: TEST-RULE-001
specialty_key: cardiology
topic_key: test_topic
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

PROD_APPROVAL_BLOCK = """
clinical_review_status: approved
reviewed_by: clinician-a
reviewed_at: "2026-01-01T12:00:00Z"
approved_by: clinician-b
approved_at: "2026-01-02T12:00:00Z"
effective_from: "2020-01-01T00:00:00Z"
"""

APPROVED_PROD_RULE_YAML = (
    DRAFT_RULE_YAML.replace("status: draft", "status: approved_prod") + PROD_APPROVAL_BLOCK
)

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


def _load_fixture(root: Path) -> None:
    ValidatedFilesystemClinicalRuleCatalogProvider.load(
        root,
        reference_at=_REF_AT,
    )


def test_repository_catalog_loads_successfully() -> None:
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(reference_at=_REF_AT)
    assert snap.knowledge_root.is_dir()
    assert "guideline:esc:htn:2024" in snap.loaded_source_ids


def test_cardiology_approved_prod_count_zero_in_repo() -> None:
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(reference_at=_REF_AT)
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()
    assert snap.active_production_rule_ids == ()


def test_empty_prod_catalog_hash_deterministic() -> None:
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(reference_at=_REF_AT)
    assert snap.production_manifest_hash("cardiology") == _EMPTY_HASH
    assert rule_set_manifest_hash(()) == _EMPTY_HASH


def test_same_rules_different_file_order_same_hash(tmp_path: Path) -> None:
    rule_a = DRAFT_RULE_YAML.replace("TEST-RULE-001", "TEST-RULE-A").replace(
        "status: draft", "status: approved_prod"
    ) + PROD_APPROVAL_BLOCK
    rule_b = DRAFT_RULE_YAML.replace("TEST-RULE-001", "TEST-RULE-B").replace(
        "status: draft", "status: approved_prod"
    ) + PROD_APPROVAL_BLOCK.replace("clinician-a", "clinician-c").replace(
        "clinician-b", "clinician-d"
    )
    root_a = _write_minimal_catalog(
        tmp_path / "a",
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/z.yaml": rule_b, "cardiology/a.yaml": rule_a},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    root_b = _write_minimal_catalog(
        tmp_path / "b",
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/a.yaml": rule_a, "cardiology/z.yaml": rule_b},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap_a = ValidatedFilesystemClinicalRuleCatalogProvider.load(root_a, reference_at=_REF_AT)
    snap_b = ValidatedFilesystemClinicalRuleCatalogProvider.load(root_b, reference_at=_REF_AT)
    assert snap_a.production_manifest_hash("cardiology") == snap_b.production_manifest_hash(
        "cardiology"
    )
    assert len(snap_a.rule_catalog.list_active_production_rules("cardiology")) == 2


def test_approved_demo_not_in_production_list(tmp_path: Path) -> None:
    demo = DRAFT_RULE_YAML.replace("status: draft", "status: approved_demo")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/demo.yaml": demo},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()


def test_draft_not_in_production_list(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/draft.yaml": DRAFT_RULE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()


def test_deprecated_not_in_production_list(tmp_path: Path) -> None:
    rule = APPROVED_PROD_RULE_YAML.replace("status: approved_prod", "status: deprecated")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/x.yaml": rule},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()


def test_retired_not_in_production_list(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("status: draft", "status: retired")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/x.yaml": rule},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()


def test_valid_approved_prod_rule_returned(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/prod.yaml": APPROVED_PROD_RULE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    active = snap.rule_catalog.list_active_production_rules("cardiology")
    assert len(active) == 1
    assert active[0].rule_id == "TEST-RULE-001"
    assert snap.production_manifest_hash("cardiology") != _EMPTY_HASH


def test_approved_prod_invalid_source_license_fails_validation(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("status: draft", "status: approved_prod") + PROD_APPROVAL_BLOCK
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/bad.yaml": rule},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError) as exc:
        _load_fixture(root)
    assert any("prod_unverified_source_license" in item for item in exc.value.issues)


def test_approved_prod_missing_clinical_approval_fails(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("status: draft", "status: approved_prod")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/bad.yaml": rule},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError):
        _load_fixture(root)


def test_unknown_source_ref_fails(tmp_path: Path) -> None:
    rule = DRAFT_RULE_YAML.replace("guideline:esc:htn:2024", "guideline:missing:2024")
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={"cardiology/bad.yaml": rule},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError) as exc:
        _load_fixture(root)
    assert any("unknown_source_ref" in item for item in exc.value.issues)


def test_duplicate_rule_id_fails(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        rules={
            "cardiology/a.yaml": DRAFT_RULE_YAML,
            "cardiology/b.yaml": DRAFT_RULE_YAML,
        },
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError):
        _load_fixture(root)


def test_duplicate_source_id_fails(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"a.yaml": ESC_SOURCE_YAML, "b.yaml": ESC_SOURCE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError):
        _load_fixture(root)


def test_duplicate_profile_id_fails(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        profiles={"a.yaml": EMPTY_PROFILE_YAML, "b.yaml": EMPTY_PROFILE_YAML},
    )
    with pytest.raises(ClinicalKnowledgeCatalogValidationError) as exc:
        _load_fixture(root)
    assert any("duplicate_profile_id" in item for item in exc.value.issues)


def test_malformed_yaml_fails(tmp_path: Path) -> None:
    root = _write_minimal_catalog(tmp_path)
    (root / "sources" / "bad.yaml").write_text("source_id: [\n  broken\n", encoding="utf-8")
    with pytest.raises(ClinicalKnowledgeCatalogValidationError):
        _load_fixture(root)


def test_path_outside_knowledge_root_rejected(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    outside = tmp_path.parent / "outside_knowledge_root.yaml"
    outside.write_text("x: 1\n", encoding="utf-8")
    with pytest.raises(ClinicalKnowledgeCatalogIntegrityError):
        load_yaml_mapping(outside, knowledge_root=root)


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privilege varies on Windows")
def test_symlink_escape_outside_root_rejected(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path / "catalog",
        sources={"esc.yaml": ESC_SOURCE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    secret = tmp_path / "secret.yaml"
    secret.write_text("x: 1\n", encoding="utf-8")
    link = root / "sources" / "evil.yaml"
    link.symlink_to(secret)
    with pytest.raises((ClinicalKnowledgeCatalogValidationError, ClinicalKnowledgeCatalogLoadError)):
        _load_fixture(root)


def test_caller_mutation_does_not_alter_provider_state(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/prod.yaml": APPROVED_PROD_RULE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    active = list(snap.rule_catalog.list_active_production_rules("cardiology"))
    active.clear()
    again = snap.rule_catalog.list_active_production_rules("cardiology")
    assert len(again) == 1


def test_canonical_hash_uses_forward_slash_neutral_json() -> None:
    from app.domain.clinical_knowledge.enums import (
        ClinicalKnowledgeReviewStatus,
        ClinicalRuleSeverity,
        ClinicalRuleStatus,
        ClinicalRuleType,
    )
    from app.domain.clinical_knowledge.models import ClinicalRule, GuidelineRef

    rule = ClinicalRule(
        rule_id="TEST-RULE-Z",
        specialty_key="cardiology",
        topic_key="t",
        rule_type=ClinicalRuleType.NEXT_BEST_QUESTION,
        status=ClinicalRuleStatus.APPROVED_PROD,
        rule_version="2.0.0",
        clinical_intent="fixture",
        input_requirements=(),
        trigger_conditions={},
        exclusion_conditions={},
        output_definition={"question_key": "k"},
        severity=ClinicalRuleSeverity.INFO,
        priority=1,
        explanation_key="e",
        rationale_key="r",
        source_refs=("guideline:b", "guideline:a"),
        guideline_refs=(GuidelineRef(source_id="guideline:a", section_ref="s"),),
        evidence_refs=(),
        clinical_review_status=ClinicalKnowledgeReviewStatus.APPROVED,
    )
    h1 = rule_set_manifest_hash((rule,))
    h2 = rule_set_manifest_hash((rule,))
    assert h1 == h2
    assert len(h1) == 64


def test_no_non_manifest_source_body_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": ESC_SOURCE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    allowed_suffixes = {".yaml", ".yml", ".json"}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.is_file() and self.suffix.lower() not in allowed_suffixes:
            raise AssertionError(f"unexpected manifest read outside allowlist: {self}")
        return original_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)


def test_rule_catalog_view_adapter(tmp_path: Path) -> None:
    root = _write_minimal_catalog(
        tmp_path,
        sources={"esc.yaml": VERIFIED_ESC_SOURCE_YAML},
        rules={"cardiology/prod.yaml": APPROVED_PROD_RULE_YAML},
        profiles={"p.yaml": EMPTY_PROFILE_YAML},
    )
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(root, reference_at=_REF_AT)
    view = snap.rule_catalog_view("cardiology")
    assert view.available is True
    assert view.catalog.list_active_production_rules("cardiology")[0].rule_id == "TEST-RULE-001"
    assert view.manifest_hash == snap.production_manifest_hash("cardiology")


def test_provider_import_boundary() -> None:
    module_path = _REPO_ROOT / "app/infrastructure/clinical_knowledge/validated_catalog_provider.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    forbidden = frozenset({"fastapi", "sqlalchemy", "httpx", "requests", "openai"})
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden


def test_ensure_manifest_path_under_root_accepts_in_tree(tmp_path: Path) -> None:
    root = tmp_path / "clinical_knowledge"
    manifest = root / "sources" / "x.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("k: v\n", encoding="utf-8")
    resolved = ensure_manifest_path_under_root(manifest, root)
    assert resolved.is_relative_to(root.resolve())


def test_validator_still_used_by_provider() -> None:
    root = repository_clinical_knowledge_root()
    direct = DefaultRuleCatalogValidator().validate_catalog(root)
    assert direct.ok
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(reference_at=_REF_AT)
    assert snap.loaded_rule_ids == ()
