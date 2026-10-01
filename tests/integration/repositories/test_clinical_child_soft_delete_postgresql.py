"""Repository integration tests for clinical child soft-delete filtering."""

from datetime import UTC, datetime

from app.application.clinical_child_soft_delete import soft_deactivate_clinical_child
from app.application.services.clinical_evidence_service import ClinicalEvidenceService
from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from tests.integration.support.factories import make_health_measurement, make_medical_record, make_patient, make_user


async def _seed_owner_patient(user_repository, patient_repository, db_session, email: str):
    owner = await user_repository.create(make_user(email=email))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()
    return owner, patient


async def test_health_measurement_repository_excludes_inactive(
    user_repository,
    patient_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    db_session,
):
    owner, patient = await _seed_owner_patient(
        user_repository,
        patient_repository,
        db_session,
        "hm-soft-filter@example.test",
    )
    active = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner.id, patient_id=patient.id),
    )
    inactive = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner.id, patient_id=patient.id, blood_glucose=99),
    )
    soft_deactivate_clinical_child(inactive)
    await health_measurement_repository.update(inactive)
    await db_session.commit()

    listed = await health_measurement_repository.list_by_owner(owner.id, patient_id=patient.id)
    assert len(listed) == 1
    assert listed[0].id == active.id
    assert await health_measurement_repository.get_by_id_and_owner(inactive.id, owner.id) is None
    assert (
        len(
            await health_measurement_repository.list_by_patient_for_analytics(
                patient.id,
            ),
        )
        == 1
    )


async def test_medical_record_repository_excludes_inactive(
    user_repository,
    patient_repository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    db_session,
):
    owner, patient = await _seed_owner_patient(
        user_repository,
        patient_repository,
        db_session,
        "mr-soft-filter@example.test",
    )
    active = await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id),
    )
    inactive = await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id, title="Inactive row"),
    )
    soft_deactivate_clinical_child(inactive, deactivated_at=datetime.now(UTC))
    await medical_record_repository.update(inactive)
    await db_session.commit()

    listed = await medical_record_repository.list_by_owner(owner.id, patient_id=patient.id)
    assert len(listed) == 1
    assert listed[0].id == active.id
    assert await medical_record_repository.get_by_id_and_owner(inactive.id, owner.id) is None


async def test_clinical_evidence_bundle_excludes_inactive_rows(
    user_repository,
    patient_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    appointment_repository,
    risk_assessment_history_repository,
    db_session,
):
    owner, patient = await _seed_owner_patient(
        user_repository,
        patient_repository,
        db_session,
        "evidence-soft-filter@example.test",
    )
    active_meas = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner.id, patient_id=patient.id),
    )
    inactive_meas = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner.id, patient_id=patient.id, blood_glucose=99),
    )
    soft_deactivate_clinical_child(inactive_meas)
    await health_measurement_repository.update(inactive_meas)

    active_rec = await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id),
    )
    inactive_rec = await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id, title="Hidden"),
    )
    soft_deactivate_clinical_child(inactive_rec, deactivated_at=datetime.now(UTC))
    await medical_record_repository.update(inactive_rec)
    await db_session.commit()

    stored_patient = await patient_repository.get_by_id(patient.id)
    assert stored_patient is not None
    service = ClinicalEvidenceService(
        health_measurement_repository,
        medical_record_repository,
        appointment_repository,
        risk_assessment_history_repository,
    )
    bundle = await service.load_evidence_bundle(stored_patient, organization_id=None)
    meas_ids = {row.id for row in bundle.health_measurements}
    rec_ids = {row.id for row in bundle.medical_records}
    assert active_meas.id in meas_ids
    assert inactive_meas.id not in meas_ids
    assert active_rec.id in rec_ids
    assert inactive_rec.id not in rec_ids
