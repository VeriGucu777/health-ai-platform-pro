"""PostgreSQL integration tests for clinical evidence and deterministic summary."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.patient_clinical_summary_service import PatientClinicalSummaryService
from app.core.exceptions import NotFoundError
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.entities.user import UserRole
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
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
from tests.integration.support.factories import (
    make_appointment,
    make_health_measurement,
    make_medical_record,
    make_patient,
    make_user,
)


async def _seed_patient_bundle(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
):
    owner = await user_repository.create(make_user(role=UserRole.DOCTOR))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()

    record = await medical_record_repository.create(
        make_medical_record(
            owner_id=owner.id,
            patient_id=patient.id,
            record_date=datetime(2026, 3, 1, tzinfo=UTC),
            diagnosis="PG diagnosis",
        ),
    )
    measurement = await health_measurement_repository.create(
        make_health_measurement(
            owner_id=owner.id,
            patient_id=patient.id,
            measured_at=datetime(2026, 3, 2, tzinfo=UTC),
            blood_glucose=99,
        ),
    )
    appointment = await appointment_repository.create(
        make_appointment(
            owner_id=owner.id,
            patient_id=patient.id,
            appointment_date=datetime(2026, 3, 10, tzinfo=UTC),
            status="scheduled",
        ),
    )
    for atype, when, prob in (
        (RiskAssessmentType.DIABETES, datetime(2026, 2, 1, tzinfo=UTC), None),
        (RiskAssessmentType.DIABETES, datetime(2026, 4, 1, tzinfo=UTC), 0.25),
        (RiskAssessmentType.HEART_DISEASE, datetime(2026, 4, 2, tzinfo=UTC), 0.1),
        (RiskAssessmentType.STROKE, datetime(2026, 4, 3, tzinfo=UTC), 0.05),
    ):
        await risk_assessment_history_repository.append(
            RiskAssessmentHistory(
                patient_id=patient.id,
                assessment_type=atype,
                assessment_status="complete",
                risk_level="low",
                score=10.0,
                probability=prob,
                model_kind=RULE_BASED_MODEL_KIND,
                model_version="rule_based_v1",
                evaluated_by_user_id=owner.id,
                evaluated_at=when,
            ),
        )
    await db_session.commit()
    return owner, patient, record, measurement, appointment


def _summary_service(db_session: AsyncSession) -> PatientClinicalSummaryService:
    patient_repository = SQLAlchemyPatientRepository(db_session)
    membership_repository = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repository = SQLAlchemyPatientAssignmentRepository(db_session)
    access_policy = DefaultPatientAccessPolicy(
        patient_repository,
        membership_repository,
        assignment_repository,
    )
    evidence = ClinicalEvidenceService(
        SQLAlchemyHealthMeasurementRepository(db_session),
        SQLAlchemyMedicalRecordRepository(db_session),
        SQLAlchemyAppointmentRepository(db_session),
        SQLAlchemyRiskAssessmentHistoryRepository(db_session),
    )
    return PatientClinicalSummaryService(patient_repository, evidence, access_policy)


@pytest.mark.asyncio
async def test_postgresql_evidence_and_summary_provenance(
    db_session: AsyncSession,
    user_repository,
    patient_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
    risk_assessment_history_repository,
) -> None:
    owner, patient, record, measurement, appointment = await _seed_patient_bundle(
        db_session,
        user_repository,
        patient_repository,
        medical_record_repository,
        health_measurement_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    service = _summary_service(db_session)
    summary, _org = await service.get_clinical_summary(
        owner.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
    )
    assert summary.summary_version == "deterministic_v1"
    assert any(i.provenance.source_id == record.id for i in summary.clinical_items)
    assert any(m.provenance.source_id == measurement.id for m in summary.recent_measurements)
    assert any(e.provenance.source_id == appointment.id for e in summary.encounters)
    diabetes = next(r for r in summary.latest_risk_assessments if r.assessment_type == "diabetes")
    assert diabetes.probability == 0.25


@pytest.mark.asyncio
async def test_postgresql_date_filter_excludes_out_of_window(
    db_session: AsyncSession,
    user_repository,
    patient_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
    risk_assessment_history_repository,
) -> None:
    owner, patient, *_rest = await _seed_patient_bundle(
        db_session,
        user_repository,
        patient_repository,
        medical_record_repository,
        health_measurement_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    service = _summary_service(db_session)
    summary, _ = await service.get_clinical_summary(
        owner.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        date_from=datetime(2026, 5, 1, tzinfo=UTC),
        date_to=datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert summary.clinical_items == []
    assert summary.recent_measurements == []
    assert summary.data_quality.no_data is True


@pytest.mark.asyncio
async def test_postgresql_inactive_patient_summary_not_found(
    db_session: AsyncSession,
    user_repository,
    patient_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
    risk_assessment_history_repository,
) -> None:
    owner, patient, *_rest = await _seed_patient_bundle(
        db_session,
        user_repository,
        patient_repository,
        medical_record_repository,
        health_measurement_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    patient.is_active = False
    await patient_repository.update(patient)
    await db_session.commit()

    service = _summary_service(db_session)
    with pytest.raises(NotFoundError):
        await service.get_clinical_summary(
            owner.id,
            UserRole.DOCTOR,
            patient_id=patient.id,
        )


@pytest.mark.asyncio
async def test_postgresql_retrieval_documents_deterministic_ids(
    db_session: AsyncSession,
    user_repository,
    patient_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
    risk_assessment_history_repository,
) -> None:
    owner, patient, record, measurement, appointment = await _seed_patient_bundle(
        db_session,
        user_repository,
        patient_repository,
        medical_record_repository,
        health_measurement_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    evidence = ClinicalEvidenceService(
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    bundle = await evidence.load_evidence_bundle(patient, organization_id=None)
    ids = {doc.evidence_id for doc in bundle.retrieval_documents}
    assert f"medical_record:{record.id}" in ids
    assert f"health_measurement:{measurement.id}" in ids
    assert f"appointment:{appointment.id}" in ids
