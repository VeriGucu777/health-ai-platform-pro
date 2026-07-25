"""Observability endpoint and middleware tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.system_health_service import ReadinessResult, SystemHealthService
from app.core.config import Settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app


@pytest.mark.asyncio
async def test_response_includes_generated_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_inbound_request_id_is_propagated(client: AsyncClient) -> None:
    inbound = "client-request-id-123"
    response = await client.get("/api/v1/health", headers={"X-Request-ID": inbound})
    assert response.headers.get("X-Request-ID") == inbound


@pytest.mark.asyncio
async def test_health_includes_uptime_seconds(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_readiness_returns_service_unavailable_when_database_is_down() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        AUTH_RATE_LIMIT_ENABLED=False,
        HEALTH_CHECK_DB_ENABLED=True,
        METRICS_ENABLED=False,
    )
    app = create_app(settings)
    app.state.system_health_service = SystemHealthService(settings, started_at=datetime.now(UTC))

    async def failing_readiness() -> ReadinessResult:
        return ReadinessResult(
            is_ready=False,
            status="not_ready",
            checks={"database": "down"},
        )

    app.state.system_health_service.check_readiness = failing_readiness  # type: ignore[method-assign]

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"] == "down"
    reset_database_engine()


@pytest.mark.asyncio
async def test_metrics_endpoint_hidden_when_disabled(client: AsyncClient) -> None:
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_metrics_endpoint_available_when_enabled() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        AUTH_RATE_LIMIT_ENABLED=False,
        HEALTH_CHECK_DB_ENABLED=False,
        METRICS_ENABLED=True,
    )
    app = create_app(settings)

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    reset_database_engine()


@pytest.mark.asyncio
async def test_app_exception_includes_request_id(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "observability-user@example.com",
            "password": "securepass123",
            "first_name": "Obs",
            "last_name": "Test",
            "role": "patient",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "observability-user@example.com", "password": "securepass123"},
    )
    token = login_response.json()["access_token"]

    response = await client.get(
        f"/api/v1/patients/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["request_id"] == response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_validation_errors_keep_fastapi_detail_format(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "success" not in body
