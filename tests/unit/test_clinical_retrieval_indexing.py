"""Clinical retrieval indexing behavior tests."""

from datetime import UTC, date, datetime
import pytest
from uuid import uuid4

from app.application.clinical_retrieval.canonical_serialization import build_canonical_text
from app.application.clinical_retrieval.content_hash import compute_content_hash
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore


def _doc(patient_id, suffix: str) -> ClinicalRetrievalDocumentDTO:
    sid = uuid4()
    return ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{sid}",
        patient_id=patient_id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=sid,
        content_fields={"title": suffix},
    )


@pytest.mark.asyncio
async def test_unchanged_evidence_skips_reembed(monkeypatch) -> None:
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
    doc = _doc(patient.id, "alpha")
    bundle = ClinicalEvidenceBundle(patient=patient, retrieval_documents=[doc])

    calls: list[int] = []
    original = provider.embed_documents

    async def counted(texts: list[str]) -> list[list[float]]:
        calls.append(len(texts))
        return await original(texts)

    monkeypatch.setattr(provider, "embed_documents", counted)

    await service.sync_patient_index(bundle)
    assert calls == [1]
    await service.sync_patient_index(bundle)
    assert calls == [1]


@pytest.mark.asyncio
async def test_changed_content_updates_hash(monkeypatch) -> None:
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
    doc = _doc(patient.id, "one")
    record = MedicalRecord(
        owner_id=patient.owner_id,
        patient_id=patient.id,
        record_date=datetime(2026, 1, 1, tzinfo=UTC),
        record_type="visit",
        title="T",
        diagnosis="alpha",
    )
    record.id = doc.source_id
    bundle = ClinicalEvidenceBundle(patient=patient, medical_records=[record], retrieval_documents=[doc])
    await service.sync_patient_index(bundle)
    record.diagnosis = "beta"
    bundle2 = ClinicalEvidenceBundle(patient=patient, medical_records=[record], retrieval_documents=[doc])
    await service.sync_patient_index(bundle2)
    states = await store.list_index_states(patient.id)
    assert len(states) == 1
    canonical = build_canonical_text(doc, bundle2)
    assert states[doc.evidence_id].content_hash == compute_content_hash(canonical)


@pytest.mark.asyncio
async def test_embedding_version_change_triggers_reembed(monkeypatch) -> None:
    store = InMemoryClinicalVectorStore()
    provider = DeterministicFakeEmbeddingProvider(embedding_version="1")
    service = ClinicalRetrievalIndexService(store, provider)
    patient = Patient(
        owner_id=uuid4(),
        first_name="A",
        last_name="B",
        date_of_birth=date(1990, 1, 1),
        gender="x",
    )
    doc = _doc(patient.id, "stable")
    bundle = ClinicalEvidenceBundle(patient=patient, retrieval_documents=[doc])

    calls: list[int] = []
    original = provider.embed_documents

    async def counted(texts: list[str]) -> list[list[float]]:
        calls.append(len(texts))
        return await original(texts)

    monkeypatch.setattr(provider, "embed_documents", counted)

    await service.sync_patient_index(bundle)
    assert calls == [1]

    provider_v2 = DeterministicFakeEmbeddingProvider(embedding_version="2")
    service_v2 = ClinicalRetrievalIndexService(store, provider_v2)

    async def counted_v2(texts: list[str]) -> list[list[float]]:
        calls.append(len(texts))
        return await DeterministicFakeEmbeddingProvider.embed_documents(provider_v2, texts)

    monkeypatch.setattr(provider_v2, "embed_documents", counted_v2)
    await service_v2.sync_patient_index(bundle)
    assert calls == [1, 1]
