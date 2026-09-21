"""PostgreSQL pgvector integration for clinical retrieval."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.application.clinical_retrieval.constants import CLINICAL_RETRIEVAL_VECTOR_DIMENSION
from app.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.clinical_retrieval_index_service import ClinicalRetrievalIndexService
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.domain.entities.user import UserRole
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
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
from tests.integration.support.factories import make_medical_record, make_patient, make_user


@pytest.mark.asyncio
async def test_pgvector_extension_and_patient_scoped_search(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    result = await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    assert result.scalar_one_or_none() == 1

    doctor = await user_repository.create(make_user(role=UserRole.DOCTOR))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=doctor.id))
    await db_session.commit()
    await medical_record_repository.create(
        make_medical_record(
            owner_id=doctor.id,
            patient_id=patient.id,
            diagnosis="integration retrieval target",
            record_date=datetime(2026, 4, 1, tzinfo=UTC),
        ),
    )
    await db_session.commit()

    patient_repo = SQLAlchemyPatientRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)
    policy = DefaultPatientAccessPolicy(patient_repo, membership_repo, assignment_repo)
    evidence = ClinicalEvidenceService(
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    embedding = DeterministicFakeEmbeddingProvider(dimensions=CLINICAL_RETRIEVAL_VECTOR_DIMENSION)
    store = SQLAlchemyClinicalVectorStore(
        db_session,
        storage_vector_dimension=CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    )
    index = ClinicalRetrievalIndexService(
        store,
        embedding,
        storage_vector_dimension=CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    )
    service = ClinicalRetrievalService(
        patient_repo,
        evidence,
        index,
        store,
        embedding,
        policy,
    )

    dto, _ = await service.search(
        doctor.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        query="integration retrieval target",
        top_k=3,
    )
    assert dto.results
    assert dto.results[0].source_type.value == "medical_record"
    assert dto.results[0].evidence_id.startswith("medical_record:")

    inactive = await patient_repository.get_by_id(patient.id)
    assert inactive is not None
    inactive.is_active = False
    await patient_repository.update(inactive)
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await service.search(
            doctor.id,
            UserRole.DOCTOR,
            patient_id=patient.id,
            query="integration retrieval target",
        )
