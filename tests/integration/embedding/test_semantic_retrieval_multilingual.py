"""Multilingual semantic retrieval smoke (TR/EN + cross-language) with real local embeddings."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.application.clinical_retrieval.constants import (
    CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
)
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.interfaces.clinical_vector_store import ClinicalVectorIndexRecord
from app.infrastructure.embeddings.local_embedding_provider import LocalEmbeddingProvider
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore
from tests.support.semantic_retrieval_harness import ALL_DEMO_EVIDENCE, APPOINTMENT, BLOOD_PRESSURE, GLUCOSE


def _assert_relevant_above_appointment(hits, relevant_id: str) -> None:
    assert hits, "expected at least one hit"
    rank = {hit.evidence_id: idx for idx, hit in enumerate(hits)}
    assert rank[relevant_id] < rank[APPOINTMENT.evidence_id]


@pytest.fixture(scope="module")
def local_provider(production_local_embedding_provider: LocalEmbeddingProvider) -> LocalEmbeddingProvider:
    assert production_local_embedding_provider.dimensions == CLINICAL_RETRIEVAL_VECTOR_DIMENSION
    return production_local_embedding_provider


async def _index_tr_evidence(store: InMemoryClinicalVectorStore, provider: LocalEmbeddingProvider, patient_id):
    texts = [item.text_tr for item in ALL_DEMO_EVIDENCE]
    vectors = await provider.embed_documents(texts)
    for item, vector in zip(ALL_DEMO_EVIDENCE, vectors, strict=True):
        await store.upsert_batch(
            [
                ClinicalVectorIndexRecord(
                    evidence_id=item.evidence_id,
                    patient_id=patient_id,
                    organization_id=None,
                    source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
                    source_id=uuid4(),
                    event_time=None,
                    canonical_text=json.dumps(
                        {"source_type": "medical_record", "demo_text": item.text_tr},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    embedding=vector,
                    embedding_model=provider.model_name,
                    embedding_version=provider.embedding_version,
                    embedding_dimension=provider.dimensions,
                    embedding_pooling_profile=provider.pooling_profile,
                    content_hash=f"hash-{item.evidence_id}",
                ),
            ],
        )


async def _index_en_evidence(store: InMemoryClinicalVectorStore, provider: LocalEmbeddingProvider, patient_id):
    texts = [item.text_en for item in ALL_DEMO_EVIDENCE]
    vectors = await provider.embed_documents(texts)
    for item, vector in zip(ALL_DEMO_EVIDENCE, vectors, strict=True):
        await store.upsert_batch(
            [
                ClinicalVectorIndexRecord(
                    evidence_id=item.evidence_id,
                    patient_id=patient_id,
                    organization_id=None,
                    source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
                    source_id=uuid4(),
                    event_time=None,
                    canonical_text=json.dumps(
                        {"source_type": "medical_record", "demo_text": item.text_en},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    embedding=vector,
                    embedding_model=provider.model_name,
                    embedding_version=provider.embedding_version,
                    embedding_dimension=provider.dimensions,
                    embedding_pooling_profile=provider.pooling_profile,
                    content_hash=f"hash-en-{item.evidence_id}",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_turkish_queries_rank_clinical_demo_evidence(local_provider: LocalEmbeddingProvider) -> None:
    store = InMemoryClinicalVectorStore()
    patient_id = uuid4()
    await _index_tr_evidence(store, local_provider, patient_id)

    glucose_query = await local_provider.embed_query("son kan şekeri ölçümü")
    glucose_hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=glucose_query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(glucose_hits, GLUCOSE.evidence_id)

    bp_query = await local_provider.embed_query("kan basıncı kayıtları")
    bp_hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=bp_query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(bp_hits, BLOOD_PRESSURE.evidence_id)


@pytest.mark.asyncio
async def test_english_queries_rank_clinical_demo_evidence(local_provider: LocalEmbeddingProvider) -> None:
    store = InMemoryClinicalVectorStore()
    patient_id = uuid4()
    await _index_en_evidence(store, local_provider, patient_id)

    glucose_query = await local_provider.embed_query("recent glucose measurements")
    glucose_hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=glucose_query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(glucose_hits, GLUCOSE.evidence_id)

    bp_query = await local_provider.embed_query("blood pressure records")
    bp_hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=bp_query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(bp_hits, BLOOD_PRESSURE.evidence_id)


@pytest.mark.asyncio
async def test_cross_language_tr_evidence_en_query(local_provider: LocalEmbeddingProvider) -> None:
    store = InMemoryClinicalVectorStore()
    patient_id = uuid4()
    await _index_tr_evidence(store, local_provider, patient_id)
    query = await local_provider.embed_query("blood pressure hypertension")
    hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(hits, BLOOD_PRESSURE.evidence_id)


@pytest.mark.asyncio
async def test_cross_language_en_evidence_tr_query(local_provider: LocalEmbeddingProvider) -> None:
    store = InMemoryClinicalVectorStore()
    patient_id = uuid4()
    await _index_en_evidence(store, local_provider, patient_id)
    query = await local_provider.embed_query("kan şekeri glukoz")
    hits = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    _assert_relevant_above_appointment(hits, GLUCOSE.evidence_id)


@pytest.mark.asyncio
async def test_retrieval_ordering_is_deterministic(local_provider: LocalEmbeddingProvider) -> None:
    store = InMemoryClinicalVectorStore()
    patient_id = uuid4()
    await _index_en_evidence(store, local_provider, patient_id)
    query = await local_provider.embed_query("glucose diabetes")
    first = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    second = await store.search_patient_scope(
        patient_id=patient_id,
        organization_id=None,
        query_embedding=query,
        top_k=3,
        active_embedding_model=local_provider.model_name,
        active_embedding_version=local_provider.embedding_version,
        active_embedding_dimension=local_provider.dimensions,
        active_embedding_pooling_profile=local_provider.pooling_profile,
    )
    assert [hit.evidence_id for hit in first] == [hit.evidence_id for hit in second]
