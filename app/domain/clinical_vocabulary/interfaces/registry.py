"""Read-only port for controlled vocabulary lookup."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.domain.clinical_vocabulary.models import ControlledVocabularyItem, ControlledVocabularyManifest


class ClinicalVocabularyRegistry(ABC):
    @abstractmethod
    def manifest(self) -> ControlledVocabularyManifest:
        """Loaded manifest metadata and full term set."""

    @abstractmethod
    def get(self, key: str) -> ControlledVocabularyItem | None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def list_by_category(self, category: VocabularyCategory) -> tuple[ControlledVocabularyItem, ...]:
        ...

    @abstractmethod
    def list_by_specialty(self, specialty: str) -> tuple[ControlledVocabularyItem, ...]:
        ...
