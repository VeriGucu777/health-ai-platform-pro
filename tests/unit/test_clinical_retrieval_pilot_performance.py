"""Pilot-scale application-layer cosine performance spot-check (no ONNX)."""

from __future__ import annotations

import time
from uuid import uuid4

import pytest

from app.application.clinical_retrieval.constants import CLINICAL_RETRIEVAL_VECTOR_DIMENSION
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.interfaces.clinical_vector_store import ClinicalVectorIndexRecord
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore


@pytest.mark.asyncio
async def test_three_hundred_candidate_search_completes_under_pilot_budget() -> None:
    store = InMemoryClinicalVectorStore()
    provider = DeterministicFakeEmbeddingProvider(dimensions=CLINICAL_RETRIEVAL_VECTOR_DIMENSION)
    patient_id = uuid4()
    records: list[ClinicalVectorIndexRecord] = []
    for index in range(300):
        vector = await provider.embed_query(f"demo evidence token {index % 17}")
        records.append(
            ClinicalVectorIndexRecord(
                evidence_id=f"medical_record:{uuid4()}",
                patient_id=patient_id,
                organization_id=None,
                source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
                source_id=uuid4(),
                event_time=None,
                canonical_text=f'{{"idx":{index}}}',
                embedding=vector,
                embedding_model=provider.model_name,
                embedding_version=provider.embedding_version,
                embedding_dimension=provider.dimensions,
                embedding_pooling_profile=provider.pooling_profile,
                content_hash=f"h-{index}",
            ),
        )
    await store.upsert_batch(records)
    query = await provider.embed_query("pilot retrieval query")
    started = time.perf_counter()
    hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=query,
        top_k=10,
        active_embedding_model=provider.model_name,
        active_embedding_version=provider.embedding_version,
        active_embedding_dimension=provider.dimensions,
        active_embedding_pooling_profile=provider.pooling_profile,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert len(hits) == 10
    assert elapsed_ms < 5000, f"300-vector pilot search took {elapsed_ms:.1f}ms"
