"""Phase 2F: chest pain pilot source metadata and license gates."""

from __future__ import annotations

import yaml

from app.application.clinical_knowledge.license_gates import validate_source_license_invariants
from app.application.clinical_knowledge.rule_catalog_validator import DefaultRuleCatalogValidator
from app.infrastructure.clinical_knowledge.validated_catalog_provider import (
    ValidatedFilesystemClinicalRuleCatalogProvider,
)
from app.domain.clinical_knowledge.enums import (
    AiUsageStatus,
    CommercialUsageStatus,
    LicenseStatus,
)
from app.infrastructure.clinical_knowledge.filesystem_catalog import (
    FilesystemClinicalKnowledgeSourceRegistry,
    load_sources_from_root,
)
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root

CHEST_PAIN_SOURCE_ID = "guideline:aha-acc:chest-pain:2021"
ACS_SOURCE_ID = "guideline:esc:acs:2023"
HTN_SOURCE_ID = "guideline:esc:htn:2024"


def test_repository_loads_chest_pain_and_acs_metadata_sources() -> None:
    root = repository_clinical_knowledge_root()
    sources = load_sources_from_root(root)
    ids = {source.source_id for source in sources}
    assert CHEST_PAIN_SOURCE_ID in ids
    assert ACS_SOURCE_ID in ids
    assert HTN_SOURCE_ID in ids


def test_new_sources_metadata_only_no_body_fields() -> None:
    root = repository_clinical_knowledge_root()
    for name in (
        "guideline_aha_acc_chest_pain_2021.yaml",
        "guideline_esc_acs_2023.yaml",
    ):
        raw = yaml.safe_load((root / "sources" / name).read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        forbidden = ("body", "content", "full_text", "recommendations", "pdf")
        for key in raw:
            assert key.lower() not in forbidden
        assert raw["content_ingestion_allowed"] is False


def test_permission_required_sources_block_ingestion_invariants() -> None:
    root = repository_clinical_knowledge_root()
    registry = FilesystemClinicalKnowledgeSourceRegistry.from_knowledge_root(root)
    for source_id in (CHEST_PAIN_SOURCE_ID, ACS_SOURCE_ID):
        source = registry.get_source(source_id)
        assert source is not None
        assert source.license_status == LicenseStatus.PERMISSION_REQUIRED
        assert source.content_ingestion_allowed is False
        assert validate_source_license_invariants(source) == []


def test_esc_sources_ai_and_commercial_permission_required_not_absolute_prohibition() -> None:
    root = repository_clinical_knowledge_root()
    registry = FilesystemClinicalKnowledgeSourceRegistry.from_knowledge_root(root)
    for source_id in (ACS_SOURCE_ID, HTN_SOURCE_ID):
        source = registry.get_source(source_id)
        assert source is not None
        assert source.ai_usage_status == AiUsageStatus.PERMISSION_REQUIRED
        assert source.commercial_usage_status == CommercialUsageStatus.PERMISSION_REQUIRED
        assert source.ai_usage_status != AiUsageStatus.PROHIBITED


def test_esc_permission_required_still_blocks_content_ingestion_via_gate() -> None:
    root = repository_clinical_knowledge_root()
    registry = FilesystemClinicalKnowledgeSourceRegistry.from_knowledge_root(root)
    acs = registry.get_source(ACS_SOURCE_ID)
    assert acs is not None
    blocked = acs.model_copy(update={"content_ingestion_allowed": True})
    issues = validate_source_license_invariants(blocked)
    assert any("permission_required" in msg for msg in issues)


def test_official_urls_present() -> None:
    root = repository_clinical_knowledge_root()
    registry = FilesystemClinicalKnowledgeSourceRegistry.from_knowledge_root(root)
    chest = registry.get_source(CHEST_PAIN_SOURCE_ID)
    acs = registry.get_source(ACS_SOURCE_ID)
    assert chest is not None and chest.official_url.startswith("https://")
    assert acs is not None and "escardio.org" in acs.official_url


def test_duplicate_source_ids_rejected_in_validator(tmp_path) -> None:
    from tests.unit.clinical_knowledge.test_rule_catalog_validator import (
        ESC_SOURCE_YAML,
        _write_minimal_catalog,
    )

    root = _write_minimal_catalog(
        tmp_path,
        sources={"a.yaml": ESC_SOURCE_YAML, "b.yaml": ESC_SOURCE_YAML},
    )
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert not result.ok


def test_catalog_validation_passes_with_new_sources() -> None:
    root = repository_clinical_knowledge_root()
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    assert result.ok, [f"{i.code}: {i.message}" for i in result.issues]


def test_active_production_rules_remain_zero() -> None:
    snap = ValidatedFilesystemClinicalRuleCatalogProvider.load(
        repository_clinical_knowledge_root(),
    )
    assert snap.rule_catalog.list_active_production_rules("cardiology") == ()
