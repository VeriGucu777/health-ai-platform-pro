"""Multi-device refresh session semantics (pilot: simultaneous logins supported)."""

import pytest
from httpx import AsyncClient

REGISTER = {
    "email": "multi-session@example.com",
    "password": "securepass123",
    "first_name": "Multi",
    "last_name": "Session",
    "role": "patient",
}


async def _login(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_two_devices_both_refresh_independently(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    device_a = await _login(client)
    device_b = await _login(client)

    refresh_a1 = device_a["refresh_token"]
    refresh_b1 = device_b["refresh_token"]
    assert refresh_a1 != refresh_b1

    after_a = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a1})
    assert after_a.status_code == 200
    refresh_a2 = after_a.json()["refresh_token"]

    after_b = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_b1})
    assert after_b.status_code == 200

    replay_a = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a1})
    assert replay_a.status_code == 401

    still_b = await client.post("/api/v1/auth/refresh", json={"refresh_token": after_b.json()["refresh_token"]})
    assert still_b.status_code == 200

    replay_b_old = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_b1})
    assert replay_b_old.status_code == 401

    refresh_a2  # used above via replay only; chain still valid
    still_a = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a2})
    assert still_a.status_code == 200


@pytest.mark.asyncio
async def test_second_login_does_not_invalidate_first_device_refresh(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    device_a = await _login(client)
    refresh_a = device_a["refresh_token"]
    await _login(client)
    still_a = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_a})
    assert still_a.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_all_device_refresh_tokens(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    device_a = await _login(client)
    device_b = await _login(client)
    rotated_b = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": device_b["refresh_token"]},
    )
    assert rotated_b.status_code == 200
    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_b.json()["refresh_token"]},
    )
    assert logout.status_code == 200
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": device_a["refresh_token"]})
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rotated_b.json()["refresh_token"]},
        )
    ).status_code == 401
