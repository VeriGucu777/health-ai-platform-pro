"""Refresh token rotation and reuse detection."""

import pytest
from httpx import AsyncClient

REGISTER = {
    "email": "rotate-user@example.com",
    "password": "securepass123",
    "first_name": "Rotate",
    "last_name": "User",
    "role": "patient",
}


@pytest.mark.asyncio
async def test_refresh_rotation_issues_new_pair(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    old_refresh = login.json()["refresh_token"]
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["refresh_token"] != old_refresh
    assert body["access_token"]


@pytest.mark.asyncio
async def test_old_refresh_replay_denied(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rotate-user@example.com", "password": "securepass123"},
    )
    old_refresh = login.json()["refresh_token"]
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_refresh_replay_audit_reason_code(
    client: AsyncClient,
    audit_log_repository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": REGISTER["password"]},
    )
    old_refresh = login.json()["refresh_token"]
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    failures = [
        entry
        for entry in audit_log_repository.list_all()
        if (entry.metadata or {}).get("reason_code") == "refresh_token_reuse"
    ]
    assert failures
