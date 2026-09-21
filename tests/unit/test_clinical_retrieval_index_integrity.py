"""Index sync integrity when embedding or upsert fails."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.core.exceptions import ValidationError
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.patient import Patient
from app.domain.interfaces.clinical_vector_store import ClinicalVectorIndexRecord
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)


class _FailingUpsertStore:
    def __init__(self, inner) -> None:
        self._inner = inner
        self.delete_called = False

    async def list_index_states(self, patient_id):
        return await self._inner.list_index_states(patient_id)

    async def upsert_batch(self, records: list[ClinicalVectorIndexRecord]) -> None:
        raise ValidationError("simulated upsert failure")

    async def delete_evidence_ids_for_patient(self, patient_id, *, keep_evidence_ids):
        self.delete_called = True
        await self._inner.delete_evidence_ids_for_patient(
            patient_id,
            keep_evidence_ids=keep_evidence_ids,
        )


class _EmbedFailProvider(DeterministicFakeEmbeddingProvider):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("simulated embedding provider failure")


@pytest.mark.asyncio
async def test_upsert_failure_does_not_run_stale_cleanup() -> None:
    from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore

    inner = InMemoryClinicalVectorStore()
    store = _FailingUpsertStore(inner)
    provider = DeterministicFakeEmbeddingProvider()
    service = ClinicalRetrievalIndexService(store, provider)
    patient = Patient(
        owner_id=uuid4(),
        first_name="A",
        last_name="B",
        date_of_birth=date(1990, 1, 1),
        gender="x",
    )
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{uuid4()}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=uuid4(),
        content_fields={"title": "x"},
    )
    bundle = ClinicalEvidenceBundle(patient=patient, retrieval_documents=[doc])
    with pytest.raises(ValidationError, match="simulated upsert"):
        await service.sync_patient_index(bundle)
    assert store.delete_called is False


@pytest.mark.asyncio
async def test_embedding_failure_leaves_existing_index_state() -> None:
    from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore

    store = InMemoryClinicalVectorStore()
    provider = DeterministicFakeEmbeddingProvider()
    service = ClinicalRetrievalIndexService(store, provider)
    patient = Patient(
        owner_id=uuid4(),
        first_name="A",
        last_name="B",
        date_of_birth=date(1990, 1, 1),
        gender="x",
    )
    sid = uuid4()
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{sid}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=sid,
        content_fields={"title": "seed"},
    )
    bundle = ClinicalEvidenceBundle(patient=patient, retrieval_documents=[doc])
    await service.sync_patient_index(bundle)
    states_before = await store.list_index_states(patient.id)

    failing = ClinicalRetrievalIndexService(store, _EmbedFailProvider())
    doc2 = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{uuid4()}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=uuid4(),
        content_fields={"title": "new"},
    )
    bundle2 = ClinicalEvidenceBundle(
        patient=patient,
        retrieval_documents=[doc, doc2],
    )
    with pytest.raises(RuntimeError, match="simulated embedding"):
        await failing.sync_patient_index(bundle2)
    states_after = await store.list_index_states(patient.id)
    assert states_before == states_after


@pytest.mark.asyncio
async def test_model_name_change_forces_reembed() -> None:
    from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore

    store = InMemoryClinicalVectorStore()
    provider_v1 = DeterministicFakeEmbeddingProvider(embedding_version="1")
    service = ClinicalRetrievalIndexService(store, provider_v1)
    patient = Patient(
        owner_id=uuid4(),
        first_name="A",
        last_name="B",
        date_of_birth=date(1990, 1, 1),
        gender="x",
    )
    sid = uuid4()
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{sid}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=sid,
        content_fields={"title": "same"},
    )
    bundle = ClinicalEvidenceBundle(patient=patient, retrieval_documents=[doc])
    await service.sync_patient_index(bundle)
    states = await store.list_index_states(patient.id)
    row = states[doc.evidence_id]
    assert row.embedding_model == provider_v1.model_name

    class _AltModelProvider(DeterministicFakeEmbeddingProvider):
        @property
        def model_name(self) -> str:
            return "deterministic_fake_v2"

    provider_v2 = _AltModelProvider(embedding_version="1")
    service_v2 = ClinicalRetrievalIndexService(store, provider_v2)
    embed_calls = 0
    original = provider_v2.embed_documents

    async def counted(texts: list[str]) -> list[list[float]]:
        nonlocal embed_calls
        embed_calls += 1
        return await original(texts)

    provider_v2.embed_documents = counted  # type: ignore[method-assign]
    await service_v2.sync_patient_index(bundle)
    assert embed_calls == 1
    states2 = await store.list_index_states(patient.id)
    row2 = states2[doc.evidence_id]
    assert row2.embedding_model == "deterministic_fake_v2"
