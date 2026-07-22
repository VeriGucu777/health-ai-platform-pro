"""Appointment CRUD endpoint integration tests."""

import pytest
from httpx import AsyncClient

PATIENT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "phone": "+15551234567",
    "notes": "Initial consultation scheduled",
}

APPOINTMENT_PAYLOAD = {
    "appointment_date": "2026-08-15T10:30:00Z",
    "appointment_type": "consultation",
    "status": "scheduled",
    "notes": "First visit",
}


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict[str, str]:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": "patient",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_appointment(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-owner@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    response = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["appointment_type"] == "consultation"
    assert data["status"] == "scheduled"
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_list_appointments(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-lister@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    create_response = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert create_response.status_code == 201

    response = await client.get("/api/v1/appointments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_list_appointments_filter_by_patient_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-filter@example.com")
    patient_a = await _create_patient(client, headers)

    patient_b_response = await client.post(
        "/api/v1/patients",
        json={**PATIENT_PAYLOAD, "first_name": "Jane"},
        headers=headers,
    )
    assert patient_b_response.status_code == 201
    patient_b = patient_b_response.json()["id"]

    for patient_id in (patient_a, patient_b):
        payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
        response = await client.post("/api/v1/appointments", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        f"/api/v1/appointments?patient_id={patient_a}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["patient_id"] == patient_a


@pytest.mark.asyncio
async def test_retrieve_appointment(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-reader@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/appointments", json=payload, headers=headers)
    appointment_id = created.json()["id"]

    response = await client.get(f"/api/v1/appointments/{appointment_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == appointment_id


@pytest.mark.asyncio
async def test_update_appointment(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-updater@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/appointments", json=payload, headers=headers)
    appointment_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/appointments/{appointment_id}",
        json={"status": "completed", "notes": "Visit completed"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["notes"] == "Visit completed"


@pytest.mark.asyncio
async def test_delete_appointment(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-deleter@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/appointments", json=payload, headers=headers)
    appointment_id = created.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/appointments/{appointment_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/appointments/{appointment_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/appointments")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_access_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="appt-owner2@example.com")
    other_headers = await _register_and_login(client, email="appt-other@example.com")

    patient_id = await _create_patient(client, owner_headers)
    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/appointments", json=payload, headers=owner_headers)
    appointment_id = created.json()["id"]

    response = await client.get(f"/api/v1/appointments/{appointment_id}", headers=other_headers)
    assert response.status_code == 404
    assert response.json()["success"] is False

    patch_response = await client.patch(
        f"/api/v1/appointments/{appointment_id}",
        json={"status": "cancelled"},
        headers=other_headers,
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/appointments/{appointment_id}",
        headers=other_headers,
    )
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_create_with_foreign_patient_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="appt-patient-owner@example.com")
    other_headers = await _register_and_login(client, email="appt-patient-other@example.com")

    patient_id = await _create_patient(client, owner_headers)
    payload = {**APPOINTMENT_PAYLOAD, "patient_id": patient_id}

    response = await client.post("/api/v1/appointments", json=payload, headers=other_headers)
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_create_with_nonexistent_patient_returns_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="appt-no-patient@example.com")

    payload = {
        **APPOINTMENT_PAYLOAD,
        "patient_id": "00000000-0000-0000-0000-000000000001",
    }
    response = await client.post("/api/v1/appointments", json=payload, headers=headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"
