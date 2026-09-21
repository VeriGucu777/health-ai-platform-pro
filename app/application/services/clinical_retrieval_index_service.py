"""Idempotent patient-scoped clinical evidence indexing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_retrieval.canonical_serialization import build_canonical_text
from app.application.clinical_retrieval.content_hash import compute_content_hash
from app.application.clinical_retrieval.index_fingerprint import compute_index_fingerprint
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.application.services.base import BaseService
from app.core.exceptions import ValidationError
from app.domain.interfaces.clinical_vector_store import ClinicalVectorIndexRecord, ClinicalVectorStore
from app.domain.interfaces.embedding_provider import EmbeddingProvider


class ClinicalRetrievalIndexService(BaseService):
    """Build/update vector index from authorized evidence bundles."""

    def __init__(
        self,
        vector_store: ClinicalVectorStore,
        embedding_provider: EmbeddingProvider,
        *,
        storage_vector_dimension: int | None = None,
    ) -> None:
        self._store = vector_store
        self._embeddings = embedding_provider
        self._storage_vector_dimension = storage_vector_dimension

    async def sync_patient_index(self, bundle: ClinicalEvidenceBundle) -> None:
        """Index all retrieval documents; skip unchanged fingerprints; purge stale evidence."""
        patient_id = bundle.patient.id
        organization_id = bundle.organization_id
        docs = bundle.retrieval_documents
        keep_ids = {doc.evidence_id for doc in docs}

        existing_states = await self._store.list_index_states(patient_id)

        pending_texts: list[str] = []
        pending_meta: list[tuple] = []

        for doc in docs:
            canonical = build_canonical_text(doc, bundle)
            content_hash = compute_content_hash(canonical)
            fingerprint = compute_index_fingerprint(
                content_hash=content_hash,
                embedding_model=self._embeddings.model_name,
                embedding_version=self._embeddings.embedding_version,
                embedding_dimension=self._embeddings.dimensions,
                embedding_pooling_profile=self._embeddings.pooling_profile,
            )
            state = existing_states.get(doc.evidence_id)
            if state is not None:
                existing_fingerprint = compute_index_fingerprint(
                    content_hash=state.content_hash,
                    embedding_model=state.embedding_model,
                    embedding_version=state.embedding_version,
                    embedding_dimension=state.embedding_dimension,
                    embedding_pooling_profile=state.embedding_pooling_profile,
                )
                if existing_fingerprint == fingerprint:
                    continue
            pending_texts.append(canonical)
            pending_meta.append((doc, canonical, content_hash))

        if pending_texts:
            vectors = await self._embeddings.embed_documents(pending_texts)
            if len(vectors) != len(pending_meta):
                raise ValidationError("Embedding batch size mismatch")
            records: list[ClinicalVectorIndexRecord] = []
            for (doc, canonical, content_hash), vector in zip(pending_meta, vectors, strict=True):
                self._validate_vector(vector)
                records.append(
                    ClinicalVectorIndexRecord(
                        evidence_id=doc.evidence_id,
                        patient_id=patient_id,
                        organization_id=organization_id,
                        source_type=doc.source_type,
                        source_id=doc.source_id,
                        event_time=doc.event_time,
                        canonical_text=canonical,
                        embedding=vector,
                        embedding_model=self._embeddings.model_name,
                        embedding_version=self._embeddings.embedding_version,
                        embedding_dimension=self._embeddings.dimensions,
                        embedding_pooling_profile=self._embeddings.pooling_profile,
                        content_hash=content_hash,
                    ),
                )
            await self._store.upsert_batch(records)

        await self._store.delete_evidence_ids_for_patient(
            patient_id,
            keep_evidence_ids=keep_ids,
        )

    def _validate_vector(self, vector: list[float]) -> None:
        if len(vector) != self._embeddings.dimensions:
            raise ValidationError(
                f"Embedding length {len(vector)} does not match provider dimension "
                f"{self._embeddings.dimensions}",
            )
        if (
            self._storage_vector_dimension is not None
            and len(vector) != self._storage_vector_dimension
        ):
            raise ValidationError(
                f"Embedding length {len(vector)} does not match storage dimension "
                f"{self._storage_vector_dimension}",
            )
