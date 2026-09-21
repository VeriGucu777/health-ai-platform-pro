"""Authorized clinical retrieval orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_retrieval.constants import (
    DEFAULT_TOP_K,
    MAX_TOP_K,
    RETRIEVAL_VERSION,
)
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.application.dtos.clinical_retrieval import ClinicalRetrievalResultDTO, PatientClinicalRetrievalDTO
from app.application.services.base import BaseService
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.application.services.patient_read_access import resolve_patient_read_access
from app.core.exceptions import ValidationError
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.user import UserRole
from app.domain.interfaces.clinical_vector_store import ClinicalVectorStore
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


class ClinicalRetrievalService(BaseService):
    """Patient-scoped semantic retrieval without LLM narrative."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        clinical_evidence_service: ClinicalEvidenceService,
        index_service: ClinicalRetrievalIndexService,
        vector_store: ClinicalVectorStore,
        embedding_provider: EmbeddingProvider,
        access_policy: PatientAccessPolicy | None = None,
    ) -> None:
        self._patients = patient_repository
        self._evidence = clinical_evidence_service
        self._index = index_service
        self._store = vector_store
        self._embeddings = embedding_provider
        self._access_policy = access_policy

    async def search(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        source_types: list[ClinicalEvidenceSourceType] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[PatientClinicalRetrievalDTO, UUID | None]:
        cleaned = query.strip()
        if not cleaned:
            raise ValidationError("query must not be empty")

        resolved = await resolve_patient_read_access(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
        )
        resolved_from = _normalize_datetime(date_from) if date_from is not None else None
        resolved_to = _normalize_datetime(date_to) if date_to is not None else None
        self._validate_date_range(resolved_from, resolved_to)
        capped_k = min(max(1, top_k), MAX_TOP_K)

        index_bundle = await self._load_index_bundle(resolved.patient, resolved.organization_id)
        await self._index.sync_patient_index(index_bundle)

        query_vector = await self._embeddings.embed_query(cleaned)
        hits = await self._store.search_patient_scope(
            patient_id=patient_id,
            organization_id=resolved.organization_id,
            query_embedding=query_vector,
            top_k=capped_k,
            active_embedding_model=self._embeddings.model_name,
            active_embedding_version=self._embeddings.embedding_version,
            active_embedding_dimension=self._embeddings.dimensions,
            active_embedding_pooling_profile=self._embeddings.pooling_profile,
            source_types=source_types,
            date_from=resolved_from,
            date_to=resolved_to,
        )

        dto = PatientClinicalRetrievalDTO(
            patient_id=patient_id,
            retrieval_version=RETRIEVAL_VERSION,
            query_received=True,
            top_k=capped_k,
            results=[
                ClinicalRetrievalResultDTO(
                    evidence_id=hit.evidence_id,
                    source_type=hit.source_type,
                    source_id=hit.source_id,
                    event_time=hit.event_time,
                    relevance_score=hit.relevance_score,
                    content_fields=hit.content_fields,
                )
                for hit in hits
            ],
        )
        return dto, resolved.organization_id

    async def _load_index_bundle(self, patient, organization_id: UUID | None) -> ClinicalEvidenceBundle:
        return await self._evidence.load_evidence_bundle(
            patient,
            organization_id=organization_id,
            date_from=None,
            date_to=None,
        )

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> None:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
