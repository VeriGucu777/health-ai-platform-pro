"""Patient clinical timeline endpoint tests."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.support.clinical_api_test_helpers import (
    TIMELINE_PATIENT_PAYLOAD as PATIENT_PAYLOAD,
    assigned_patient_for_doctor,
    register_and_login,
)

_register_and_login = register_and_login


@pytest.mark.asyncio
async def test_clinical_timeline_happy_path(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="timeline-owner@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )

    record_date = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "visit",
            "title": "Annual visit",
            "diagnosis": "Hypertension",
        },
        headers=headers,
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["truncated"] is False
    assert "disclaimer" in data
    assert any(
        event["event_type"] == "medical_record_diagnosis" for event in data["events"]
    )


@pytest.mark.asyncio
async def test_clinical_timeline_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/patients/00000000-0000-4000-8000-000000000099/clinical-timeline",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_clinical_timeline_cross_user_not_found(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_email = "timeline-owner2@example.com"
    other_email = "timeline-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)

    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        patient_payload=PATIENT_PAYLOAD,
        extra_org_doctor_emails=(other_email,),
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=other_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_clinical_timeline_empty(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="timeline-empty@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.asyncio
async def test_clinical_timeline_invalid_date_range(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="timeline-range@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )

    date_from = datetime.now(UTC).isoformat()
    date_to = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        params={"date_from": date_from, "date_to": date_to},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_clinical_timeline_lab_result_event_type(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="timeline-lab@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )

    record_date = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "lab_result",
            "title": "Lipid panel",
            "diagnosis": "LDL 142 mg/dL",
        },
        headers=headers,
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert any(
        event["event_type"] == "medical_record_lab_result" for event in data["events"]
    )


@pytest.mark.asyncio
async def test_clinical_timeline_mixed_glucose_no_increasing_trend_warning(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="timeline-glucose@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )

    await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_id,
            "measured_at": datetime(2026, 4, 20, 8, 0, tzinfo=UTC).isoformat(),
            "blood_glucose": 104,
            "glucose_context": "fasting",
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_id,
            "measured_at": datetime(2026, 5, 18, 9, 0, tzinfo=UTC).isoformat(),
            "blood_glucose": 118,
            "glucose_context": "post_meal",
        },
        headers=headers,
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        params={
            "date_from": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
            "date_to": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    events = response.json()["events"]
    assert not any(event["event_type"] == "measurement_trend_derived" for event in events)
    assert any(
        event["event_type"] == "measurement_trend_insufficient_comparable"
        for event in events
    )
