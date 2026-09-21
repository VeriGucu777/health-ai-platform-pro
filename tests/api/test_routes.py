"""Verify all expected routes are registered."""

import pytest
from httpx import ASGITransport, AsyncClient


EXPECTED_OPENAPI_PATHS = {
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/me",
    "/api/v1/auth/admin/ping",
    "/api/v1/patients",
    "/api/v1/patients/{patient_id}",
    "/api/v1/patients/{patient_id}/reports/health-summary.pdf",
    "/api/v1/patients/{patient_id}/clinical-timeline",
    "/api/v1/patients/{patient_id}/risk-assessments/diabetes",
    "/api/v1/patients/{patient_id}/risk-assessments/heart-disease",
    "/api/v1/patients/{patient_id}/risk-assessments/stroke",
    "/api/v1/appointments",
    "/api/v1/appointments/{appointment_id}",
    "/api/v1/medical-records",
    "/api/v1/medical-records/{medical_record_id}",
    "/api/v1/health-measurements",
    "/api/v1/health-measurements/{health_measurement_id}",
    "/api/v1/health-measurements/analytics/summary",
    "/api/v1/health-measurements/analytics/trends",
    "/api/v1/health-measurements/analytics/insights",
}


@pytest.mark.asyncio
async def test_all_v1_routes_registered(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"].keys())
    assert EXPECTED_OPENAPI_PATHS.issubset(paths)


@pytest.mark.asyncio
async def test_custom_api_prefix() -> None:
    """Router factory must honour a custom API prefix."""
    from app.core.config import Settings as SettingsClass
    from app.infrastructure.database.session import reset_database_engine
    from app.main import create_app

    custom = SettingsClass(
        ENVIRONMENT="development",
        API_V1_PREFIX="/api/custom/v1",
        JWT_SECRET_KEY="test-secret",
    )
    reset_database_engine()
    test_app = create_app(custom)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/custom/v1/health")
        assert response.status_code == 200

    reset_database_engine()
