"""Authentication endpoint integration tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from tests.support.memory_user_repository import InMemoryUserRepository

REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "securepass123",
    "first_name": "Alice",
    "last_name": "Smith",
    "role": "patient",
}


@pytest.mark.asyncio
async def test_successful_registration(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["role"] == "patient"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_duplicate_email_rejection(client: AsyncClient) -> None:
    first = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert first.status_code == 201

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "first_name": "Bob"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["success"] is False
    assert "already registered" in duplicate.json()["message"].lower()


@pytest.mark.asyncio
async def test_email_normalized_to_lowercase(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "  ALICE@Example.COM  "},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_successful_login(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_incorrect_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_logout(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_role_authorization_denies_patient(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_authorization_allows_system_admin(
    client: AsyncClient,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.create(
        User(
            email="admin@example.com",
            hashed_password=hash_password("adminpass123"),
            first_name="Admin",
            last_name="User",
            role=UserRole.SYSTEM_ADMIN,
        )
    )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Admin access granted"


@pytest.mark.asyncio
async def test_self_register_rejects_system_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "bad@example.com", "role": "system_admin"},
    )
    assert response.status_code == 403
