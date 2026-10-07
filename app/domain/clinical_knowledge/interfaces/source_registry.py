"""Port for read-only clinical knowledge source registry."""

from abc import ABC, abstractmethod

from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource


class ClinicalKnowledgeSourceRegistry(ABC):
    """Lookup bibliographic and license metadata for knowledge sources."""

    @abstractmethod
    def get_source(self, source_id: str) -> ClinicalKnowledgeSource | None:
        """Return one source by stable identifier."""

    @abstractmethod
    def list_sources(self) -> tuple[ClinicalKnowledgeSource, ...]:
        """Return all sources in deterministic order."""

    @abstractmethod
    def exists(self, source_id: str) -> bool:
        """Return whether a source id is registered."""
