"""In-memory ClinicalVectorStore for API tests."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_retrieval.canonical_serialization import content_fields_from_canonical
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.interfaces.clinical_vector_store import (
    ClinicalVectorIndexRecord,
    ClinicalVectorIndexState,
    ClinicalVectorSearchHit,
    ClinicalVectorStore,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class InMemoryClinicalVectorStore(ClinicalVectorStore):
    """Simple dict-backed vector index."""

    def __init__(self) -> None:
        self._rows: dict[str, ClinicalVectorIndexRecord] = {}

    async def list_index_states(self, patient_id: UUID) -> dict[str, ClinicalVectorIndexState]:
        return {
            eid: ClinicalVectorIndexState(
                content_hash=row.content_hash,
                embedding_model=row.embedding_model,
                embedding_version=row.embedding_version,
                embedding_dimension=row.embedding_dimension,
                embedding_pooling_profile=row.embedding_pooling_profile,
            )
            for eid, row in self._rows.items()
            if row.patient_id == patient_id
        }

    async def upsert_batch(self, records: list[ClinicalVectorIndexRecord]) -> None:
        for record in records:
            self._rows[record.evidence_id] = record

    async def delete_evidence_ids_for_patient(
        self,
        patient_id: UUID,
        *,
        keep_evidence_ids: set[str],
    ) -> None:
        to_delete = [
            eid
            for eid, row in self._rows.items()
            if row.patient_id == patient_id and eid not in keep_evidence_ids
        ]
        for eid in to_delete:
            del self._rows[eid]

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
        candidates = [
            row
            for row in self._rows.values()
            if row.patient_id == patient_id
            and row.organization_id == organization_id
            and row.embedding_model == active_embedding_model
            and row.embedding_version == active_embedding_version
            and row.embedding_dimension == active_embedding_dimension
            and row.embedding_pooling_profile == active_embedding_pooling_profile
        ]
        if source_types:
            allowed = {st.value for st in source_types}
            candidates = [r for r in candidates if r.source_type.value in allowed]
        if date_from is not None:
            start = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
            candidates = [r for r in candidates if r.event_time is None or r.event_time >= start]
        if date_to is not None:
            end = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
            candidates = [r for r in candidates if r.event_time is None or r.event_time <= end]

        scored = [(_cosine_similarity(query_embedding, r.embedding), r) for r in candidates]
        scored.sort(
            key=lambda item: (
                -item[0],
                -(item[1].event_time.timestamp() if item[1].event_time else 0.0),
                item[1].evidence_id,
            ),
        )
        hits: list[ClinicalVectorSearchHit] = []
        for score, row in scored[:top_k]:
            hits.append(
                ClinicalVectorSearchHit(
                    evidence_id=row.evidence_id,
                    patient_id=row.patient_id,
                    organization_id=row.organization_id,
                    source_type=row.source_type,
                    source_id=row.source_id,
                    event_time=row.event_time,
                    relevance_score=round(score, 6),
                    content_fields=content_fields_from_canonical(row.canonical_text),
                ),
            )
        return hits
