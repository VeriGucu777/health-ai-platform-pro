"""Phase 2 P0: minimal clinical RBAC and token_version revocation tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.domain.entities.user import User, UserRole
from tests.support.memory_user_repository import InMemoryUserRepository

PATIENT_PAYLOAD = {
    "first_name": "Clinical",
    "last_name": "Subject",
    "date_of_birth": "1990-01-01",
    "gender": "male",
}


async def _register_login(
    client: AsyncClient,
    *,
    email: str,
    role: str,
    password: str = "securepass123",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_doctor_can_access_clinical_patients_route(client: AsyncClient) -> None:
    headers = await _register_login(client, email="rbac-doctor@example.com", role="doctor")
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clinic_admin_can_access_clinical_patients_route(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.create(
        User(
            email="rbac-clinic-admin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Clinic",
            last_name="Admin",
            role=UserRole.CLINIC_ADMIN,
        )
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rbac-clinic-admin@example.com", "password": "securepass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_patient_denied_clinical_patients_route(client: AsyncClient) -> None:
    headers = await _register_login(client, email="rbac-patient@example.com", role="patient")
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_role_denied_clinical_route(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.create(
        User(
            email="rbac-sysadmin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        )
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rbac-sysadmin@example.com", "password": "securepass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patient_denied_clinical_timeline_route(client: AsyncClient) -> None:
    doctor_headers = await _register_login(client, email="rbac-doc-tl@example.com", role="doctor")
    created = await client.post(
        "/api/v1/patients",
        json=PATIENT_PAYLOAD,
        headers=doctor_headers,
    )
    patient_id = created.json()["id"]

    patient_headers = await _register_login(
        client,
        email="rbac-pat-tl@example.com",
        role="patient",
    )
    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=patient_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_invalid_after_logout(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout-revoke@example.com",
            "password": "securepass123",
            "first_name": "Logout",
            "last_name": "User",
            "role": "doctor",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "logout-revoke@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 200

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_token_version_mismatch_rejects_access(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
    test_settings,
) -> None:
    user = await user_repository.create(
        User(
            email="tv-mismatch@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Token",
            last_name="Mismatch",
            role=UserRole.DOCTOR,
            token_version=1,
        )
    )
    stale_token = create_access_token(
        user.id,
        settings=test_settings,
        extra_claims={"role": user.role.value, "tv": 0},
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {stale_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_invalidates_existing_tokens(client: AsyncClient) -> None:
    email = f"pwd-change-{uuid4()}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Pwd",
            "last_name": "Change",
            "role": "doctor",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newsecurepass456"},
        headers=headers,
    )
    assert change.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401
