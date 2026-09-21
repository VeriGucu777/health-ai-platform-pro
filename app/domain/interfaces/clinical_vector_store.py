"""Clinical vector store port — patient-scoped retrieval only."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType


@dataclass(frozen=True)
class ClinicalVectorIndexState:
    """Persisted index metadata for incremental sync."""

    content_hash: str
    embedding_model: str
    embedding_version: str
    embedding_dimension: int
    embedding_pooling_profile: str


@dataclass(frozen=True)
class ClinicalVectorIndexRecord:
    """One indexed retrieval vector row."""

    evidence_id: str
    patient_id: UUID
    organization_id: UUID | None
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None
    canonical_text: str
    embedding: list[float]
    embedding_model: str
    embedding_version: str
    embedding_dimension: int
    embedding_pooling_profile: str
    content_hash: str


@dataclass(frozen=True)
class ClinicalVectorSearchHit:
    """Authorized search hit with provenance and score."""

    evidence_id: str
    patient_id: UUID
    organization_id: UUID | None
    source_type: ClinicalEvidenceSourceType
    source_id: UUID
    event_time: datetime | None
    relevance_score: float
    content_fields: dict[str, str]


class ClinicalVectorStore(ABC):
    """Patient-scoped vector index operations."""

    @abstractmethod
    async def list_index_states(self, patient_id: UUID) -> dict[str, ClinicalVectorIndexState]:
        """Return evidence_id → index state for incremental indexing."""

    @abstractmethod
    async def upsert_batch(self, records: list[ClinicalVectorIndexRecord]) -> None:
        """Insert or update vectors by evidence_id."""

    @abstractmethod
    async def delete_evidence_ids_for_patient(
        self,
        patient_id: UUID,
        *,
        keep_evidence_ids: set[str],
    ) -> None:
        """Remove stale vectors not present in the current evidence set."""

    @abstractmethod
    async def search_patient_scope(
        self,
        *,
        patient_id: UUID,
        organization_id: UUID | None,
        query_embedding: list[float],
        top_k: int,
        active_embedding_model: str,
        active_embedding_version: str,
        active_embedding_dimension: int,
        active_embedding_pooling_profile: str,
        source_types: list[ClinicalEvidenceSourceType] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[ClinicalVectorSearchHit]:
        """Semantic search limited to one authorized patient scope."""
