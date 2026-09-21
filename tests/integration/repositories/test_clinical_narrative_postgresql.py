"""PostgreSQL integration for clinical narrative (fake LLM provider)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.clinical_narrative.constants import NARRATIVE_VERSION
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.clinical_narrative_service import ClinicalNarrativeService
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.patient_clinical_summary_service import PatientClinicalSummaryService
from app.core.config import Settings
from app.domain.entities.user import UserRole
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from app.infrastructure.llm.deterministic_fake_narrative_generator import (
    DeterministicFakeNarrativeGenerator,
)
from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
from app.infrastructure.repositories.clinical_retrieval_vector_repository import (
    SQLAlchemyClinicalVectorStore,
)
from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.patient_assignment_repository import (
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.risk_assessment_history_repository import (
    SQLAlchemyRiskAssessmentHistoryRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.repositories.test_clinical_summary_postgresql import _seed_patient_bundle


@pytest.mark.asyncio
async def test_clinical_narrative_pg_fake_provider_provenance(
    db_session: AsyncSession,
    user_repository,
    patient_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
    risk_assessment_history_repository,
) -> None:
    owner, patient, _record, _measurement, _appointment = await _seed_patient_bundle(
        db_session,
        user_repository,
        patient_repository,
        medical_record_repository,
        health_measurement_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    patient_repo = patient_repository
    record_repo = medical_record_repository
    measurement_repo = health_measurement_repository
    appointment_repo = appointment_repository
    risk_repo = risk_assessment_history_repository
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)
    access = DefaultPatientAccessPolicy(patient_repo, membership_repo, assignment_repo)
    evidence = ClinicalEvidenceService(measurement_repo, record_repo, appointment_repo, risk_repo)
    embedding = DeterministicFakeEmbeddingProvider(dimensions=384)
    vector_store = SQLAlchemyClinicalVectorStore(db_session, storage_vector_dimension=384)
    index = ClinicalRetrievalIndexService(vector_store, embedding, storage_vector_dimension=384)
    retrieval = ClinicalRetrievalService(
        patient_repo,
        evidence,
        index,
        vector_store,
        embedding,
        access,
    )
    summary = PatientClinicalSummaryService(patient_repo, evidence, access)
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="fake",
        FAKE_EMBEDDING_DIMENSIONS=384,
        CLINICAL_NARRATIVE_PROVIDER="fake",
    )
    service = ClinicalNarrativeService(
        patient_repo,
        retrieval,
        summary,
        DeterministicFakeNarrativeGenerator(),
        settings,
        access,
    )
    dto, _org = await service.generate_narrative(
        owner.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        query="postgresql integration overview",
        language="en",
    )
    assert dto.narrative_version == NARRATIVE_VERSION
    assert dto.narrative
    assert dto.fallback_used is False
    if dto.evidence_references:
        assert dto.evidence_references[0].evidence_id
