"""Patient CRUD endpoint integration tests."""

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


@pytest.mark.asyncio
async def test_create_patient(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="owner@example.com")

    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["gender"] == "male"
    assert data["is_active"] is True
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_list_patients(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="lister@example.com")

    create_response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert create_response.status_code == 201

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["first_name"] == "John"


@pytest.mark.asyncio
async def test_retrieve_patient(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="reader@example.com")

    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = created.json()["id"]

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == patient_id


@pytest.mark.asyncio
async def test_update_patient(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="updater@example.com")

    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"first_name": "Jane", "notes": "Updated notes"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_delete_patient(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="deleter@example.com")

    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = created.json()["id"]

    delete_response = await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patients")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_access_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="owner2@example.com")
    other_headers = await _register_and_login(client, email="other@example.com")

    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=owner_headers)
    patient_id = created.json()["id"]

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=other_headers)
    assert response.status_code == 404
    assert response.json()["success"] is False

    patch_response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"first_name": "Hacker"},
        headers=other_headers,
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(f"/api/v1/patients/{patient_id}", headers=other_headers)
    assert delete_response.status_code == 404
