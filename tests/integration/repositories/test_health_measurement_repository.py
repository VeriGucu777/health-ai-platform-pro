"""SQLAlchemy health measurement repository integration tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import (
    make_health_measurement,
    make_patient,
    make_user,
    random_owner_id,
)

async def _seed_owner_and_patient(user_repository, patient_repository, db_session, email: str):
    owner = await user_repository.create(make_user(email=email))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()
    return owner, patient


async def test_create_and_get_by_id_and_owner(
    user_repository,
    patient_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    db_session,
):
    owner, patient = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "measure-owner@example.test",
    )
    created = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner.id, patient_id=patient.id),
    )
    await db_session.commit()

    loaded = await health_measurement_repository.get_by_id_and_owner(created.id, owner.id)
    assert loaded is not None
    assert loaded.blood_glucose == Decimal("110.5")


async def test_cross_user_isolation(
    user_repository,
    patient_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    db_session,
):
    owner_one, patient_one = await _seed_owner_and_patient(
        user_repository,
        patient_repository,
        db_session,
        "measure-owner-one@example.test",
    )
    owner_two = await user_repository.create(make_user(email="measure-owner-two@example.test"))
    await db_session.commit()

    created = await health_measurement_repository.create(
        make_health_measurement(owner_id=owner_one.id, patient_id=patient_one.id),
    )
    await db_session.commit()

    assert await health_measurement_repository.get_by_id_and_owner(created.id, owner_one.id) is not None
    assert await health_measurement_repository.get_by_id_and_owner(created.id, owner_two.id) is None


async def test_list_count_and_analytics_filters(
    user_repository,
    patient_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="measure-list@example.test"))
    await db_session.commit()
    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()

    base_time = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    await health_measurement_repository.create(
        make_health_measurement(
            owner_id=owner.id,
            patient_id=patient.id,
            measured_at=base_time,
            glucose_context="fasting",
            blood_glucose=Decimal("95.0"),
        ),
    )
    await health_measurement_repository.create(
        make_health_measurement(
            owner_id=owner.id,
            patient_id=patient.id,
            measured_at=base_time + timedelta(days=1),
            glucose_context="post_meal",
            blood_glucose=Decimal("140.0"),
        ),
    )
    await db_session.commit()

    filtered = await health_measurement_repository.list_by_owner(
        owner.id,
        patient_id=patient.id,
        glucose_context="fasting",
    )
    assert len(filtered) == 1

    count = await health_measurement_repository.count_by_owner(
        owner.id,
        patient_id=patient.id,
        date_from=base_time,
        date_to=base_time + timedelta(hours=1),
    )
    assert count == 1

    analytics_rows = await health_measurement_repository.list_by_owner_for_analytics(
        owner.id,
        patient_id=patient.id,
    )
    assert len(analytics_rows) == 2
    assert analytics_rows[0].measured_at <= analytics_rows[1].measured_at


async def test_foreign_key_requires_existing_patient(
    user_repository,
    health_measurement_repository: SQLAlchemyHealthMeasurementRepository,
    db_session,
):
    owner = await user_repository.create(make_user(email="measure-fk@example.test"))
    await db_session.commit()

    measurement = make_health_measurement(owner_id=owner.id, patient_id=random_owner_id())
    with pytest.raises(IntegrityError):
        await health_measurement_repository.create(measurement)
    await db_session.rollback()
