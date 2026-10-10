"""Path helpers for vocabulary manifests under clinical_knowledge/."""

from pathlib import Path

from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root


def repository_vocabulary_root() -> Path:
    return repository_clinical_knowledge_root() / "vocabularies"
