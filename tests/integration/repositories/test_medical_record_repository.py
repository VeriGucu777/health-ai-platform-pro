"""SQLAlchemy medical record repository integration tests."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_medical_record, make_patient, make_user, random_owner_id

async def _seed_owner_and_patient(user_repository, patient_repository, db_session, email: str):
    owner = await user_repository.create(make_user(email=email))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()
    return owner, patient


async def test_create_and_get_by_id_and_owner(
    user_repository,
    patient_repository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    db_session,
):
    owner, patient = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "record-owner@example.test",
    )
    created = await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id),
    )
    await db_session.commit()

    loaded = await medical_record_repository.get_by_id_and_owner(created.id, owner.id)
    assert loaded is not None
    assert loaded.title.startswith("Integration Record")


async def test_cross_user_isolation(
    user_repository,
    patient_repository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    db_session,
):
    owner_one, patient_one = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "record-owner-one@example.test",
    )
    owner_two = await user_repository.create(make_user(email="record-owner-two@example.test"))
    await db_session.commit()

    created = await medical_record_repository.create(
        make_medical_record(owner_id=owner_one.id, patient_id=patient_one.id),
    )
    await db_session.commit()

    assert await medical_record_repository.get_by_id_and_owner(created.id, owner_one.id) is not None
    assert await medical_record_repository.get_by_id_and_owner(created.id, owner_two.id) is None


async def test_list_and_count_with_filters(
    user_repository,
    patient_repository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="record-list@example.test"))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()

    await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id, record_type="visit"),
    )
    await medical_record_repository.create(
        make_medical_record(owner_id=owner.id, patient_id=patient.id, record_type="lab"),
    )
    await db_session.commit()

    visit_records = await medical_record_repository.list_by_owner(
        owner.id,
        patient_id=patient.id,
        record_type="visit",
    )
    assert len(visit_records) == 1
    assert await medical_record_repository.count_by_owner(owner.id, record_type="lab") == 1


async def test_foreign_key_requires_existing_patient(
    user_repository,
    medical_record_repository: SQLAlchemyMedicalRecordRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="record-fk@example.test"))
    await db_session.commit()

    record = make_medical_record(owner_id=owner.id, patient_id=random_owner_id())
    with pytest.raises(IntegrityError):
        await medical_record_repository.create(record)
    await db_session.rollback()
