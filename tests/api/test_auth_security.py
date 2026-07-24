"""Security-focused authentication endpoint tests."""

from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.api.deps import get_auth_service
from app.application.services.auth_service import AuthService
from app.core.config import Settings
from app.core.security import create_refresh_token
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app
from tests.support.memory_user_repository import InMemoryUserRepository

REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "securepass123",
    "first_name": "Alice",
    "last_name": "Smith",
    "role": "patient",
}

RATE_LIMITED_REGISTER_PAYLOAD = {
    "email": "security-user@example.com",
    "password": "securepass123",
    "first_name": "Security",
    "last_name": "User",
    "role": "patient",
}


@pytest.fixture
def rate_limited_settings() -> Settings:
    return Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        AUTH_RATE_LIMIT_ENABLED=True,
        AUTH_LOGIN_RATE_LIMIT=2,
        AUTH_LOGIN_RATE_WINDOW_SECONDS=60,
        AUTH_REFRESH_RATE_LIMIT=2,
        AUTH_REFRESH_RATE_WINDOW_SECONDS=60,
        AUTH_REGISTER_RATE_LIMIT=10,
    )


@pytest.fixture
async def rate_limited_client(rate_limited_settings: Settings):
    user_repository = InMemoryUserRepository()
    app = create_app(rate_limited_settings)

    def override_auth_service(request: Request) -> AuthService:
        return AuthService(user_repository, request.app.state.settings)

    app.dependency_overrides[get_auth_service] = override_auth_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, user_repository, app
    app.dependency_overrides.clear()
    reset_database_engine()


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(rate_limited_client) -> None:
    client, _user_repository, _app = rate_limited_client
    await client.post("/api/v1/auth/register", json=RATE_LIMITED_REGISTER_PAYLOAD)

    login_payload = {"email": "security-user@example.com", "password": "wrongpassword"}
    for _ in range(2):
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 401

    blocked = await client.post("/api/v1/auth/login", json=login_payload)
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["success"] is False
    assert "too many requests" in body["message"].lower()
    assert "password" not in body["message"].lower()


@pytest.mark.asyncio
async def test_refresh_rate_limit_returns_429(rate_limited_client) -> None:
    client, _user_repository, _app = rate_limited_client
    await client.post("/api/v1/auth/register", json=RATE_LIMITED_REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "security-user@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200
    assert second.status_code == 200

    blocked = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert blocked.status_code == 429
    assert blocked.json()["success"] is False


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    access_token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["message"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_refresh_rejects_malformed_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-valid-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token(
    rate_limited_client,
    rate_limited_settings: Settings,
) -> None:
    client, user_repository, _app = rate_limited_client
    user = await user_repository.get_by_email("security-user@example.com")
    if user is None:
        await client.post("/api/v1/auth/register", json=RATE_LIMITED_REGISTER_PAYLOAD)
        user = await user_repository.get_by_email("security-user@example.com")
    assert user is not None

    expired_refresh = create_refresh_token(
        user.id,
        settings=rate_limited_settings,
        expires_delta=timedelta(seconds=-1),
    )

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_refresh},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_existing_login_and_refresh_behavior_preserved(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_me_rejects_refresh_token_as_bearer(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
