"""Authentication token revocation tests."""

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "email": "revoke@example.com",
    "password": "securepass123",
    "first_name": "Revoke",
    "last_name": "Test",
    "role": "patient",
}


@pytest.mark.asyncio
async def test_logout_invalidates_previous_access_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "revoke@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    me_before = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_before.status_code == 200

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 200

    me_after = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_previous_refresh_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "revoke@example.com", "password": "securepass123"},
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
