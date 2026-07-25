"""SQLAlchemy patient repository integration tests."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_patient, make_user, random_owner_id

async def test_create_and_get_by_id_and_owner(
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="patient-owner@example.test"))
    await db_session.commit()

    patient = make_patient(owner_id=owner.id)
    created = await patient_repository.create(patient)
    await db_session.commit()

    loaded = await patient_repository.get_by_id_and_owner(created.id, owner.id)
    assert loaded is not None
    assert loaded.first_name == patient.first_name


async def test_cross_user_isolation_for_get(
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    db_session,
):
    owner_one = await user_repository.create(make_user(email="owner-one@example.test"))
    owner_two = await user_repository.create(make_user(email="owner-two@example.test"))
    await db_session.commit()

    created = await patient_repository.create(make_patient(owner_id=owner_one.id))
    await db_session.commit()

    assert await patient_repository.get_by_id_and_owner(created.id, owner_one.id) is not None
    assert await patient_repository.get_by_id_and_owner(created.id, owner_two.id) is None


async def test_list_and_count_by_owner(
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    db_session,
):
    owner_one = await user_repository.create(make_user(email="list-owner-one@example.test"))
    owner_two = await user_repository.create(make_user(email="list-owner-two@example.test"))
    await db_session.commit()

    await patient_repository.create(make_patient(owner_id=owner_one.id, first_name="A"))
    await patient_repository.create(make_patient(owner_id=owner_one.id, first_name="B"))
    await patient_repository.create(make_patient(owner_id=owner_two.id, first_name="C"))
    await db_session.commit()

    owner_one_patients = await patient_repository.list_by_owner(owner_one.id)
    assert len(owner_one_patients) == 2
    assert await patient_repository.count_by_owner(owner_one.id) == 2
    assert await patient_repository.count_by_owner(owner_two.id) == 1


async def test_update_and_delete_patient(
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="patient-crud@example.test"))
    await db_session.commit()

    created = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()

    created.notes = "updated notes"
    created.touch()
    await patient_repository.update(created)
    await db_session.commit()

    loaded = await patient_repository.get_by_id_and_owner(created.id, owner.id)
    assert loaded is not None
    assert loaded.notes == "updated notes"

    deleted = await patient_repository.delete(created.id)
    await db_session.commit()
    assert deleted is True
    assert await patient_repository.get_by_id_and_owner(created.id, owner.id) is None


async def test_foreign_key_requires_existing_owner(
    patient_repository: SQLAlchemyPatientRepository,
    db_session,
):
    patient = make_patient(owner_id=random_owner_id())
    with pytest.raises(IntegrityError):
        await patient_repository.create(patient)
    await db_session.rollback()
