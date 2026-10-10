"""Phase 2A controlled vocabulary foundation tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from app.application.clinical_vocabulary.manifest_hash import vocabulary_manifest_hash
from app.application.clinical_vocabulary.vocabulary_validator import DefaultVocabularyValidator
from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root
from app.infrastructure.clinical_vocabulary.filesystem_registry import (
    FilesystemClinicalVocabularyRegistry,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMAS = _REPO_ROOT / "clinical_knowledge" / "schemas"
_CARDIO_YAML = (
    _REPO_ROOT / "clinical_knowledge" / "vocabularies" / "cardiology" / "cardiology_v1.0.0.yaml"
)


def test_registry_loads_cardiology_manifest() -> None:
    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    manifest = registry.manifest()
    assert manifest.vocabulary_id == "cardiology"
    assert manifest.vocabulary_version == "1.0.0"
    assert registry.exists("card.complaint.chest_pain")
    complaints = registry.list_by_category(VocabularyCategory.COMPLAINT)
    assert len(complaints) == 7


def test_pilot_cardiology_term_counts() -> None:
    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    assert len(registry.list_by_category(VocabularyCategory.COMPLAINT)) == 7
    assert len(registry.list_by_category(VocabularyCategory.FINDING)) == 9
    assert len(registry.list_by_category(VocabularyCategory.QUESTION)) == 5
    assert len(registry.list_by_category(VocabularyCategory.VITAL)) == 4
    assert len(registry.list_by_category(VocabularyCategory.UNIT)) == 3
    assert len(registry.list_by_category(VocabularyCategory.ANSWER_CODE)) == 3
    assert len(registry.list_by_category(VocabularyCategory.ONSET)) == 4
    assert len(registry.manifest().terms) == 35


def test_no_item_claims_clinical_approval() -> None:
    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    for term in registry.manifest().terms:
        assert term.clinical_review_status.value != "clinically_approved"
        assert term.engine_safe is False


def test_manifest_hash_deterministic_and_order_independent(tmp_path: Path) -> None:
    registry = FilesystemClinicalVocabularyRegistry.default_cardiology()
    manifest = registry.manifest()
    hash_a = vocabulary_manifest_hash(manifest)
    hash_b = vocabulary_manifest_hash(manifest)
    assert hash_a == hash_b
    assert len(hash_a) == 64

    shuffled = yaml.safe_load(_CARDIO_YAML.read_text(encoding="utf-8"))
    terms = shuffled["terms"]
    shuffled["terms"] = list(reversed(terms))
    catalog = tmp_path / "clinical_knowledge"
    shutil.copytree(_SCHEMAS, catalog / "schemas")
    (catalog / "vocabularies" / "cardiology").mkdir(parents=True)
    (catalog / "vocabularies" / "cardiology" / "cardiology_v1.0.0.yaml").write_text(
        yaml.dump(shuffled, sort_keys=False),
        encoding="utf-8",
    )
    registry_shuffled = FilesystemClinicalVocabularyRegistry.from_knowledge_root(catalog)
    assert vocabulary_manifest_hash(registry_shuffled.manifest()) == hash_a


def test_validator_rejects_duplicate_key(tmp_path: Path) -> None:
    catalog = tmp_path / "clinical_knowledge"
    shutil.copytree(_SCHEMAS, catalog / "schemas")
    (catalog / "vocabularies" / "cardiology").mkdir(parents=True)
    data = yaml.safe_load(_CARDIO_YAML.read_text(encoding="utf-8"))
    data["terms"].append(dict(data["terms"][0]))
    (catalog / "vocabularies" / "cardiology" / "dup.yaml").write_text(
        yaml.dump(data, sort_keys=False),
        encoding="utf-8",
    )
    result = DefaultVocabularyValidator().validate_catalog(catalog)
    assert not result.ok
    assert any(issue.code == "duplicate_key" for issue in result.issues)


def test_validator_rejects_invalid_key_pattern(tmp_path: Path) -> None:
    catalog = tmp_path / "clinical_knowledge"
    shutil.copytree(_SCHEMAS, catalog / "schemas")
    (catalog / "vocabularies" / "cardiology").mkdir(parents=True)
    data = yaml.safe_load(_CARDIO_YAML.read_text(encoding="utf-8"))
    data["terms"][0]["key"] = "Chest Pain"
    (catalog / "vocabularies" / "cardiology" / "bad.yaml").write_text(
        yaml.dump(data, sort_keys=False),
        encoding="utf-8",
    )
    result = DefaultVocabularyValidator().validate_catalog(catalog)
    assert not result.ok


def test_validator_rejects_replacement_cycle(tmp_path: Path) -> None:
    catalog = tmp_path / "clinical_knowledge"
    shutil.copytree(_SCHEMAS, catalog / "schemas")
    (catalog / "vocabularies" / "cardiology").mkdir(parents=True)
    data = {
        "vocabulary_id": "cardiology",
        "vocabulary_version": "1.0.0",
        "specialty": "cardiology",
        "pilot_scope": "test",
        "manifest_clinical_review_status": "not_reviewed",
        "terms": [
            {
                "key": "card.complaint.a",
                "category": "complaint",
                "status": "deprecated",
                "version_added": "1.0.0",
                "display_key": "vocab.a",
                "clinical_review_status": "not_reviewed",
                "replacement_key": "card.complaint.b",
            },
            {
                "key": "card.complaint.b",
                "category": "complaint",
                "status": "deprecated",
                "version_added": "1.0.0",
                "display_key": "vocab.b",
                "clinical_review_status": "not_reviewed",
                "replacement_key": "card.complaint.a",
            },
        ],
    }
    (catalog / "vocabularies" / "cardiology" / "cycle.yaml").write_text(
        yaml.dump(data, sort_keys=False),
        encoding="utf-8",
    )
    result = DefaultVocabularyValidator().validate_catalog(catalog)
    assert not result.ok
    assert any(issue.code == "replacement_cycle" for issue in result.issues)


def test_validator_rejects_path_escape(tmp_path: Path) -> None:
    catalog = tmp_path / "clinical_knowledge"
    shutil.copytree(_SCHEMAS, catalog / "schemas")
    (catalog / "vocabularies").mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("vocabulary_id: x\n", encoding="utf-8")
    from app.infrastructure.clinical_knowledge.yaml_loader import load_yaml_mapping

    from app.application.clinical_knowledge.exceptions import ClinicalKnowledgeCatalogIntegrityError

    with pytest.raises(ClinicalKnowledgeCatalogIntegrityError, match="escapes"):
        load_yaml_mapping(outside, knowledge_root=catalog)


def test_repository_catalog_passes_validation() -> None:
    root = repository_clinical_knowledge_root()
    result = DefaultVocabularyValidator().validate_catalog(root)
    assert result.ok, [f"{i.code}: {i.message}" for i in result.issues]


def test_labels_resolve_tr_en() -> None:
    term = FilesystemClinicalVocabularyRegistry.default_cardiology().get("card.complaint.chest_pain")
    assert term is not None
    assert term.labels is not None
    assert term.labels.en == "Chest pain"
    assert "Göğüs" in term.labels.tr


def test_vocabulary_yaml_has_no_clinical_interpretation_fields() -> None:
    raw = yaml.safe_load(_CARDIO_YAML.read_text(encoding="utf-8"))
    serialized = json.dumps(raw).lower()
    for forbidden in ("diagnosis", "threshold", "treatment", "probability", "red_flag"):
        assert forbidden not in serialized
