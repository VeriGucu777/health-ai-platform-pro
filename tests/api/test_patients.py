"""Patient CRUD endpoint integration tests (org RBAC: clinic admin create, assigned doctor access)."""

from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.support.org_assigned_patient_harness import (
    PATIENT_PAYLOAD,
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
    register_clinic_admin_and_login,
)


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict[str, str]:
    return await register_and_login_doctor(
        client,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )


@pytest.mark.asyncio
async def test_create_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    admin_headers, _, _ = await register_clinic_admin_and_login(
        client,
        user_repository,
        membership_repository,
        email="owner@example.com",
    )

    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["gender"] == "male"
    assert data["is_active"] is True
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_list_patients(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "lister@example.com"
    headers = await _register_and_login(client, email=email)
    await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["first_name"] == "John"


@pytest.mark.asyncio
async def test_retrieve_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "reader@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == patient_id


@pytest.mark.asyncio
async def test_update_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "updater@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )

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
async def test_delete_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    email = "deleter@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )

    delete_response = await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert get_response.status_code == 404

    stored = await patient_repository.get_by_id(UUID(patient_id))
    assert stored is not None
    assert stored.is_active is False


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patients")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_access_returns_not_found(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_email = "owner2@example.com"
    other_email = "other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        extra_org_doctor_emails=(other_email,),
    )

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
