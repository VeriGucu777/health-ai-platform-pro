"""Map YAML manifest dicts to domain vocabulary models."""

from __future__ import annotations

from typing import Any

from app.domain.clinical_vocabulary.enums import (
    VocabularyCategory,
    VocabularyClinicalReviewStatus,
    VocabularyItemStatus,
)
from app.domain.clinical_vocabulary.models import (
    ControlledVocabularyItem,
    ControlledVocabularyManifest,
    VocabularyLabels,
    VocabularySynonyms,
)


def _engine_safe_for_item(status: VocabularyItemStatus, review: VocabularyClinicalReviewStatus) -> bool:
    return (
        status == VocabularyItemStatus.APPROVED_PROD
        and review == VocabularyClinicalReviewStatus.CLINICALLY_APPROVED
    )


def _synonyms_from_dict(raw: dict[str, Any] | None) -> VocabularySynonyms | None:
    if not raw:
        return None
    en = tuple(str(x).strip() for x in raw.get("en", []) if str(x).strip())
    tr = tuple(str(x).strip() for x in raw.get("tr", []) if str(x).strip())
    if not en and not tr:
        return None
    return VocabularySynonyms(en=en, tr=tr)


def _labels_from_dict(raw: dict[str, Any] | None) -> VocabularyLabels | None:
    if not raw:
        return None
    en = str(raw.get("en", "")).strip()
    tr = str(raw.get("tr", "")).strip()
    if not en or not tr:
        return None
    return VocabularyLabels(en=en, tr=tr)


def term_from_dict(raw: dict[str, Any]) -> ControlledVocabularyItem:
    status = VocabularyItemStatus(str(raw["status"]))
    review = VocabularyClinicalReviewStatus(str(raw["clinical_review_status"]))
    allowed = tuple(str(code) for code in raw.get("allowed_answer_codes") or ())
    return ControlledVocabularyItem(
        key=str(raw["key"]),
        category=VocabularyCategory(str(raw["category"])),
        status=status,
        version_added=str(raw["version_added"]),
        display_key=str(raw["display_key"]),
        description_key=str(raw["description_key"]).strip() if raw.get("description_key") else None,
        labels=_labels_from_dict(raw.get("labels")),
        synonyms=_synonyms_from_dict(raw.get("synonyms")),
        engine_safe=_engine_safe_for_item(status, review),
        clinical_review_status=review,
        replacement_key=str(raw["replacement_key"]) if raw.get("replacement_key") else None,
        external_system=str(raw["external_system"]) if raw.get("external_system") else None,
        external_code=str(raw["external_code"]) if raw.get("external_code") else None,
        allowed_answer_codes=allowed,
        default_unit_key=str(raw["default_unit_key"]) if raw.get("default_unit_key") else None,
    )


def manifest_from_dict(raw: dict[str, Any]) -> ControlledVocabularyManifest:
    terms = tuple(term_from_dict(item) for item in raw.get("terms") or [])
    return ControlledVocabularyManifest(
        vocabulary_id=str(raw["vocabulary_id"]),
        vocabulary_version=str(raw["vocabulary_version"]),
        specialty=str(raw["specialty"]),
        pilot_scope=str(raw["pilot_scope"]),
        manifest_clinical_review_status=VocabularyClinicalReviewStatus(
            str(raw["manifest_clinical_review_status"]),
        ),
        terms=terms,
    )
