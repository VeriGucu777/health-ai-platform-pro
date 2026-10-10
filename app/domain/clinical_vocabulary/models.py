"""Domain models for git-versioned controlled vocabulary manifests."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.clinical_vocabulary.enums import (
    VocabularyCategory,
    VocabularyClinicalReviewStatus,
    VocabularyItemStatus,
)


@dataclass(frozen=True, slots=True)
class VocabularySynonyms:
    en: tuple[str, ...] = ()
    tr: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VocabularyLabels:
    en: str
    tr: str


@dataclass(frozen=True, slots=True)
class ControlledVocabularyItem:
    key: str
    category: VocabularyCategory
    status: VocabularyItemStatus
    version_added: str
    display_key: str
    description_key: str | None = None
    labels: VocabularyLabels | None = None
    synonyms: VocabularySynonyms | None = None
    engine_safe: bool = False
    clinical_review_status: VocabularyClinicalReviewStatus = VocabularyClinicalReviewStatus.NOT_REVIEWED
    replacement_key: str | None = None
    external_system: str | None = None
    external_code: str | None = None
    allowed_answer_codes: tuple[str, ...] = ()
    default_unit_key: str | None = None


@dataclass(frozen=True, slots=True)
class ControlledVocabularyManifest:
    vocabulary_id: str
    vocabulary_version: str
    specialty: str
    pilot_scope: str
    manifest_clinical_review_status: VocabularyClinicalReviewStatus
    terms: tuple[ControlledVocabularyItem, ...] = field(default_factory=tuple)
