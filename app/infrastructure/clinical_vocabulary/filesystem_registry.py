"""Load controlled vocabulary manifests from clinical_knowledge/vocabularies/."""

from __future__ import annotations

from pathlib import Path

from app.application.clinical_vocabulary.exceptions import ClinicalVocabularyLoadError
from app.domain.clinical_vocabulary.enums import VocabularyCategory
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.clinical_vocabulary.models import ControlledVocabularyItem, ControlledVocabularyManifest
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root
from app.infrastructure.clinical_vocabulary.mapping import manifest_from_dict
from app.infrastructure.clinical_knowledge.yaml_loader import (
    iter_manifest_yaml_files_recursive,
    load_yaml_mapping,
)


def load_vocabulary_manifests_from_root(knowledge_root: Path) -> tuple[ControlledVocabularyManifest, ...]:
    root = knowledge_root.resolve()
    vocab_dir = root / "vocabularies"
    if not vocab_dir.is_dir():
        return ()

    manifests: list[ControlledVocabularyManifest] = []
    seen_ids: set[tuple[str, str]] = set()

    for path in iter_manifest_yaml_files_recursive(vocab_dir):
        try:
            data = load_yaml_mapping(path, knowledge_root=root)
            manifest = manifest_from_dict(data)
        except (ValueError, KeyError, TypeError) as exc:
            raise ClinicalVocabularyLoadError(f"{path}: {exc}") from exc
        identity = (manifest.vocabulary_id, manifest.vocabulary_version)
        if identity in seen_ids:
            raise ClinicalVocabularyLoadError(
                f"duplicate vocabulary manifest {manifest.vocabulary_id}@{manifest.vocabulary_version} in {path}",
            )
        seen_ids.add(identity)
        manifests.append(manifest)

    return tuple(manifests)


class FilesystemClinicalVocabularyRegistry(ClinicalVocabularyRegistry):
    """Read-only registry backed by validated filesystem manifests."""

    def __init__(self, manifest: ControlledVocabularyManifest) -> None:
        self._manifest = manifest
        self._by_key = {term.key: term for term in manifest.terms}

    @classmethod
    def from_knowledge_root(
        cls,
        knowledge_root: Path,
        *,
        vocabulary_id: str = "cardiology",
        vocabulary_version: str | None = None,
    ) -> FilesystemClinicalVocabularyRegistry:
        manifests = load_vocabulary_manifests_from_root(knowledge_root)
        selected: ControlledVocabularyManifest | None = None
        for manifest in manifests:
            if manifest.vocabulary_id != vocabulary_id:
                continue
            if vocabulary_version is not None and manifest.vocabulary_version != vocabulary_version:
                continue
            if selected is not None:
                raise ClinicalVocabularyLoadError(
                    f"multiple manifests match vocabulary_id={vocabulary_id!r}",
                )
            selected = manifest
        if selected is None:
            raise ClinicalVocabularyLoadError(
                f"no vocabulary manifest for vocabulary_id={vocabulary_id!r}",
            )
        return cls(selected)

    @classmethod
    def default_cardiology(cls) -> FilesystemClinicalVocabularyRegistry:
        return cls.from_knowledge_root(repository_clinical_knowledge_root())

    def manifest(self) -> ControlledVocabularyManifest:
        return self._manifest

    def get(self, key: str) -> ControlledVocabularyItem | None:
        return self._by_key.get(key)

    def exists(self, key: str) -> bool:
        return key in self._by_key

    def list_by_category(self, category: VocabularyCategory) -> tuple[ControlledVocabularyItem, ...]:
        return tuple(term for term in self._manifest.terms if term.category == category)

    def list_by_specialty(self, specialty: str) -> tuple[ControlledVocabularyItem, ...]:
        if self._manifest.specialty != specialty:
            return ()
        return self._manifest.terms
