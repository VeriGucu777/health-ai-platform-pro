"""PostgreSQL pgvector implementation of ClinicalVectorStore."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.clinical_retrieval.canonical_serialization import content_fields_from_canonical
from app.core.exceptions import ValidationError
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.interfaces.clinical_vector_store import (
    ClinicalVectorIndexRecord,
    ClinicalVectorIndexState,
    ClinicalVectorSearchHit,
    ClinicalVectorStore,
)
from app.infrastructure.database.models.clinical_retrieval_vector import ClinicalRetrievalVectorModel


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class SQLAlchemyClinicalVectorStore(ClinicalVectorStore):
    """Patient-scoped pgvector store."""

    def __init__(self, session: AsyncSession, *, storage_vector_dimension: int) -> None:
        self._session = session
        self._storage_vector_dimension = storage_vector_dimension

    async def list_index_states(self, patient_id: UUID) -> dict[str, ClinicalVectorIndexState]:
        stmt = select(
            ClinicalRetrievalVectorModel.evidence_id,
            ClinicalRetrievalVectorModel.content_hash,
            ClinicalRetrievalVectorModel.embedding_model,
            ClinicalRetrievalVectorModel.embedding_version,
            ClinicalRetrievalVectorModel.embedding_dimension,
            ClinicalRetrievalVectorModel.embedding_pooling_profile,
        ).where(ClinicalRetrievalVectorModel.patient_id == patient_id)
        result = await self._session.execute(stmt)
        return {
            row[0]: ClinicalVectorIndexState(
                content_hash=row[1],
                embedding_model=row[2],
                embedding_version=row[3],
                embedding_dimension=row[4],
                embedding_pooling_profile=row[5],
            )
            for row in result.all()
        }

    async def upsert_batch(self, records: list[ClinicalVectorIndexRecord]) -> None:
        if not records:
            return
        now = datetime.now(UTC)
        for record in records:
            self._validate_record(record)
            stmt = insert(ClinicalRetrievalVectorModel).values(
                id=uuid4(),
                patient_id=record.patient_id,
                organization_id=record.organization_id,
                evidence_id=record.evidence_id,
                source_type=record.source_type.value,
                source_id=record.source_id,
                event_time=record.event_time,
                canonical_text=record.canonical_text,
                content_hash=record.content_hash,
                embedding_model=record.embedding_model,
                embedding_version=record.embedding_version,
                embedding_dimension=record.embedding_dimension,
                embedding_pooling_profile=record.embedding_pooling_profile,
                embedding=record.embedding,
                indexed_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[ClinicalRetrievalVectorModel.evidence_id],
                set_={
                    "patient_id": record.patient_id,
                    "organization_id": record.organization_id,
                    "source_type": record.source_type.value,
                    "source_id": record.source_id,
                    "event_time": record.event_time,
                    "canonical_text": record.canonical_text,
                    "content_hash": record.content_hash,
                    "embedding_model": record.embedding_model,
                    "embedding_version": record.embedding_version,
                    "embedding_dimension": record.embedding_dimension,
                    "embedding_pooling_profile": record.embedding_pooling_profile,
                    "embedding": record.embedding,
                    "indexed_at": now,
                    "updated_at": now,
                },
            )
            await self._session.execute(stmt)
        await self._session.flush()

    def _validate_record(self, record: ClinicalVectorIndexRecord) -> None:
        if record.embedding_dimension != self._storage_vector_dimension:
            raise ValidationError(
                f"Record embedding_dimension {record.embedding_dimension} does not match "
                f"storage vector dimension {self._storage_vector_dimension}",
            )
        if len(record.embedding) != self._storage_vector_dimension:
            raise ValidationError(
                f"Embedding vector length {len(record.embedding)} does not match "
                f"storage vector dimension {self._storage_vector_dimension}",
            )

    async def delete_evidence_ids_for_patient(
        self,
        patient_id: UUID,
        *,
        keep_evidence_ids: set[str],
    ) -> None:
        stmt = delete(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.patient_id == patient_id,
        )
        if keep_evidence_ids:
            stmt = stmt.where(
                ClinicalRetrievalVectorModel.evidence_id.notin_(keep_evidence_ids),
            )
        await self._session.execute(stmt)
        await self._session.flush()

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
        if len(query_embedding) != active_embedding_dimension:
            raise ValidationError("Query embedding dimension mismatch")

        stmt = select(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.patient_id == patient_id,
            ClinicalRetrievalVectorModel.embedding_model == active_embedding_model,
            ClinicalRetrievalVectorModel.embedding_version == active_embedding_version,
            ClinicalRetrievalVectorModel.embedding_dimension == active_embedding_dimension,
            ClinicalRetrievalVectorModel.embedding_pooling_profile == active_embedding_pooling_profile,
        )
        if organization_id is None:
            stmt = stmt.where(ClinicalRetrievalVectorModel.organization_id.is_(None))
        else:
            stmt = stmt.where(ClinicalRetrievalVectorModel.organization_id == organization_id)

        if source_types:
            values = [st.value for st in source_types]
            stmt = stmt.where(ClinicalRetrievalVectorModel.source_type.in_(values))

        if date_from is not None:
            start = date_from if date_from.tzinfo else date_from.replace(tzinfo=UTC)
            stmt = stmt.where(ClinicalRetrievalVectorModel.event_time >= start)
        if date_to is not None:
            end = date_to if date_to.tzinfo else date_to.replace(tzinfo=UTC)
            stmt = stmt.where(ClinicalRetrievalVectorModel.event_time <= end)

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        scored: list[tuple[float, ClinicalRetrievalVectorModel]] = []
        for row in rows:
            score = _cosine_similarity(query_embedding, list(row.embedding))
            scored.append((score, row))

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
                    source_type=ClinicalEvidenceSourceType(row.source_type),
                    source_id=row.source_id,
                    event_time=row.event_time,
                    relevance_score=round(score, 6),
                    content_fields=content_fields_from_canonical(row.canonical_text),
                ),
            )
        return hits
