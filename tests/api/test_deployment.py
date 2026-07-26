"""API tests for WS5 deployment behavior."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app


@pytest.fixture
def production_settings() -> Settings:
    return Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        AUTH_RATE_LIMIT_ENABLED=False,
    )


@pytest.fixture
async def production_client(production_settings: Settings):
    reset_database_engine()
    application = create_app(production_settings)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    reset_database_engine()


@pytest.mark.asyncio
async def test_production_root_returns_service_json(production_client: AsyncClient) -> None:
    response = await production_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Health AI Platform Pro"
    assert data["environment"] == "production"
    assert data["health"] == "/api/v1/health"
    assert data["ready"] == "/api/v1/ready"


@pytest.mark.asyncio
async def test_production_root_does_not_redirect_to_docs(production_client: AsyncClient) -> None:
    response = await production_client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers.get("location") != "/docs"


@pytest.mark.asyncio
async def test_health_endpoint_remains_compatible(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_endpoint_remains_compatible(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
