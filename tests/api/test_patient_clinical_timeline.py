"""Patient clinical timeline endpoint tests."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

PATIENT_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Timeline",
    "date_of_birth": "1985-03-10",
    "gender": "female",
}


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": "doctor",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_clinical_timeline_happy_path(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="timeline-owner@example.com")
    patient = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = patient.json()["id"]

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
async def test_clinical_timeline_cross_user_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="timeline-owner2@example.com")
    other_headers = await _register_and_login(client, email="timeline-other@example.com")

    patient = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=owner_headers)
    patient_id = patient.json()["id"]

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=other_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_clinical_timeline_empty(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="timeline-empty@example.com")
    patient = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = patient.json()["id"]

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.asyncio
async def test_clinical_timeline_invalid_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="timeline-range@example.com")
    patient = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = patient.json()["id"]

    date_from = datetime.now(UTC).isoformat()
    date_to = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        params={"date_from": date_from, "date_to": date_to},
        headers=headers,
    )
    assert response.status_code == 422
