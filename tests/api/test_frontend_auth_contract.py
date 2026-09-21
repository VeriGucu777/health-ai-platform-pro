"""Frontend auth API contract tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_frontend_login_contract(client: AsyncClient) -> None:
    register_payload = {
        "email": "frontend@example.com",
        "password": "securepass123",
        "first_name": "Frontend",
        "last_name": "User",
        "role": "patient",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "frontend@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_frontend_register_contract(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "frontend-register@example.com",
            "password": "securepass123",
            "first_name": "Frontend",
            "last_name": "Register",
            "role": "patient",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "frontend-register@example.com"
    assert "id" in body
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_frontend_logout_contract(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "frontend-logout@example.com",
            "password": "securepass123",
            "first_name": "Frontend",
            "last_name": "Logout",
            "role": "patient",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "frontend-logout@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
