"""API tests for health measurement and medical record soft-delete."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.support.clinical_api_test_helpers import (
    TIMELINE_PATIENT_PAYLOAD as PATIENT_PAYLOAD,
    assigned_patient_for_doctor,
    register_and_login,
)

MEASUREMENT_PAYLOAD = {
    "measured_at": datetime.now(UTC).isoformat(),
    "blood_glucose": 108,
    "glucose_context": "fasting",
}


@pytest.mark.asyncio
async def test_delete_health_measurement_soft_hides_from_list_and_timeline(
    client: AsyncClient,
    user_repository,
    membership_repository,
    health_measurement_repository,
) -> None:
    headers = await register_and_login(client, email="soft-meas-api@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    created = await client.post(
        "/api/v1/health-measurements",
        json={**MEASUREMENT_PAYLOAD, "patient_id": patient_id},
        headers=headers,
    )
    assert created.status_code == 201
    measurement_id = created.json()["id"]

    timeline_before = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert timeline_before.status_code == 200
    assert timeline_before.json()["events"]

    delete_response = await client.delete(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=headers,
    )
    assert get_response.status_code == 404

    listed = await client.get("/api/v1/health-measurements", headers=headers)
    assert listed.status_code == 200
    assert all(item["id"] != measurement_id for item in listed.json()["items"])

    stored = await health_measurement_repository.get_by_id(UUID(measurement_id))
    assert stored is not None
    assert stored.is_active is False
    assert stored.deleted_at is not None

    timeline_after = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert timeline_after.status_code == 200
    source_ids = {event["source"]["id"] for event in timeline_after.json()["events"]}
    assert measurement_id not in source_ids


@pytest.mark.asyncio
async def test_delete_medical_record_soft_hides_from_list(
    client: AsyncClient,
    user_repository,
    membership_repository,
    medical_record_repository,
) -> None:
    headers = await register_and_login(client, email="soft-record-api@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    record_date = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    created = await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "visit",
            "title": "Soft delete visit",
        },
        headers=headers,
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    assert (
        await client.delete(f"/api/v1/medical-records/{record_id}", headers=headers)
    ).status_code == 204

    listed = await client.get("/api/v1/medical-records", headers=headers)
    assert all(item["id"] != record_id for item in listed.json()["items"])

    stored = await medical_record_repository.get_by_id(UUID(record_id))
    assert stored is not None and stored.is_active is False
