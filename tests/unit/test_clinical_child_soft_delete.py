"""Unit tests for clinical child soft-delete behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.clinical_child_soft_delete import soft_deactivate_clinical_child
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository


def test_soft_deactivate_idempotent():
    meas = HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=datetime.now(UTC),
        blood_glucose=100,
    )
    when = datetime(2026, 1, 1, tzinfo=UTC)
    soft_deactivate_clinical_child(meas, deactivated_at=when)
    assert meas.is_active is False
    assert meas.deleted_at == when
    first_updated = meas.updated_at
    soft_deactivate_clinical_child(meas, deactivated_at=when)
    assert meas.updated_at == first_updated


@pytest.mark.asyncio
async def test_repository_hides_inactive_health_measurement():
    repo = InMemoryHealthMeasurementRepository()
    owner_id = uuid4()
    patient_id = uuid4()
    now = datetime.now(UTC)
    active = await repo.create(
        HealthMeasurement(
            owner_id=owner_id,
            patient_id=patient_id,
            measured_at=now,
            systolic_pressure=120,
            diastolic_pressure=80,
        ),
    )
    await repo.create(
        HealthMeasurement(
            owner_id=owner_id,
            patient_id=patient_id,
            measured_at=now,
            systolic_pressure=140,
            diastolic_pressure=90,
            is_active=False,
            deleted_at=now,
        ),
    )
    listed = await repo.list_by_owner(owner_id, patient_id=patient_id)
    assert len(listed) == 1
    assert listed[0].id == active.id
    analytics = await repo.list_by_patient_for_analytics(patient_id)
    assert len(analytics) == 1


@pytest.mark.asyncio
async def test_repository_hides_inactive_medical_record():
    repo = InMemoryMedicalRecordRepository()
    owner_id = __import__("uuid").uuid4()
    patient_id = __import__("uuid").uuid4()
    now = datetime.now(UTC)
    active = await repo.create(
        MedicalRecord(
            owner_id=owner_id,
            patient_id=patient_id,
            record_date=now,
            record_type="visit",
            title="Active",
        ),
    )
    await repo.create(
        MedicalRecord(
            owner_id=owner_id,
            patient_id=patient_id,
            record_date=now,
            record_type="visit",
            title="Inactive",
            is_active=False,
            deleted_at=now,
        ),
    )
    listed = await repo.list_by_owner(owner_id, patient_id=patient_id)
    assert len(listed) == 1
    assert listed[0].id == active.id
    assert await repo.get_by_id_and_owner(active.id, owner_id) is not None
