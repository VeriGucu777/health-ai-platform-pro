"""SQLAlchemy appointment repository integration tests."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_appointment, make_patient, make_user, random_owner_id

async def _seed_owner_and_patient(user_repository, patient_repository, db_session, email: str):
    owner = await user_repository.create(make_user(email=email))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()
    return owner, patient


async def test_create_and_get_by_id_and_owner(
    user_repository,
    patient_repository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    db_session,
):
    owner, patient = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "appt-owner@example.test",
    )
    created = await appointment_repository.create(
        make_appointment(owner_id=owner.id, patient_id=patient.id),
    )
    await db_session.commit()

    loaded = await appointment_repository.get_by_id_and_owner(created.id, owner.id)
    assert loaded is not None
    assert loaded.patient_id == patient.id


async def test_cross_user_isolation(
    user_repository,
    patient_repository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    db_session,
):
    owner_one, patient_one = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "appt-owner-one@example.test",
    )
    owner_two = await user_repository.create(make_user(email="appt-owner-two@example.test"))
    await db_session.commit()

    created = await appointment_repository.create(
        make_appointment(owner_id=owner_one.id, patient_id=patient_one.id),
    )
    await db_session.commit()

    assert await appointment_repository.get_by_id_and_owner(created.id, owner_one.id) is not None
    assert await appointment_repository.get_by_id_and_owner(created.id, owner_two.id) is None


async def test_list_and_count_with_patient_filter(
    user_repository,
    patient_repository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="appt-list@example.test"))
    await db_session.commit()
    patient_one = await patient_repository.create(make_patient(owner_id=owner.id, first_name="P1"))
    patient_two = await patient_repository.create(make_patient(owner_id=owner.id, first_name="P2"))
    await db_session.commit()

    await appointment_repository.create(make_appointment(owner_id=owner.id, patient_id=patient_one.id))
    await appointment_repository.create(make_appointment(owner_id=owner.id, patient_id=patient_one.id))
    await appointment_repository.create(make_appointment(owner_id=owner.id, patient_id=patient_two.id))
    await db_session.commit()

    filtered = await appointment_repository.list_by_owner(owner.id, patient_id=patient_one.id)
    assert len(filtered) == 2
    assert await appointment_repository.count_by_owner(owner.id, patient_id=patient_one.id) == 2
    assert await appointment_repository.count_by_owner(owner.id) == 3


async def test_foreign_key_requires_existing_patient(
    user_repository,
    appointment_repository: SQLAlchemyAppointmentRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="appt-fk@example.test"))
    await db_session.commit()

    appointment = make_appointment(owner_id=owner.id, patient_id=random_owner_id())
    with pytest.raises(IntegrityError):
        await appointment_repository.create(appointment)
    await db_session.rollback()
