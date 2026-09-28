"""API security response headers."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.infrastructure.database.session import reset_database_engine
from app.main import create_app


@pytest.fixture
def staging_app():
    reset_database_engine()
    settings = Settings(
        ENVIRONMENT="staging",
        JWT_SECRET_KEY="z" * 40,
        DEBUG=False,
        HEALTH_CHECK_DB_ENABLED=False,
        METRICS_ENABLED=False,
    )
    app = create_app(settings)
    yield app
    reset_database_engine()


@pytest.fixture
async def staging_client(staging_app):
    transport = ASGITransport(app=staging_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_staging_health_includes_security_headers(staging_client: AsyncClient) -> None:
    response = await staging_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers.get("Content-Security-Policy", "")
    assert response.headers.get("Strict-Transport-Security", "").startswith("max-age=")


@pytest.mark.asyncio
async def test_development_health_has_headers_without_hsts(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Strict-Transport-Security" not in response.headers
