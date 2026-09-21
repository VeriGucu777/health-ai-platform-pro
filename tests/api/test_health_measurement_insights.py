"""Health measurement insights endpoint integration tests."""

import pytest
from httpx import AsyncClient

from app.core.reference_ranges import INSIGHTS_DISCLAIMER

PATIENT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
}

INSIGHTS_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


async def _register_and_login(client: AsyncClient, *, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "role": "doctor",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def _create_measurement(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    patient_id: str,
    measured_at: str,
    blood_glucose: int | None = None,
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
    weight_kg: float | None = None,
) -> None:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "measured_at": measured_at,
    }
    if blood_glucose is not None:
        payload["blood_glucose"] = blood_glucose
    if glucose_context is not None:
        payload["glucose_context"] = glucose_context
    if systolic_pressure is not None:
        payload["systolic_pressure"] = systolic_pressure
    if diastolic_pressure is not None:
        payload["diastolic_pressure"] = diastolic_pressure
    if heart_rate is not None:
        payload["heart_rate"] = heart_rate
    if weight_kg is not None:
        payload["weight_kg"] = weight_kg

    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 201


def _glucose_insight(data: dict) -> dict:
    return next(item for item in data["insights"] if item["metric"] == "blood_glucose")


@pytest.mark.asyncio
async def test_insights_returns_structured_response(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-structure@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == patient_id
    assert "date_from" in data
    assert "date_to" in data
    assert data["overall_status"] in {"normal", "info", "warning", "urgent"}
    assert len(data["insights"]) == 5
    assert data["disclaimer"] == INSIGHTS_DISCLAIMER
    assert "not a diagnosis" in data["disclaimer"]


@pytest.mark.asyncio
async def test_insights_normal_measurements(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-normal@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=95,
        glucose_context="fasting",
        systolic_pressure=110,
        diastolic_pressure=75,
        heart_rate=72,
        weight_kg=70.0,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    glucose = _glucose_insight(data)
    assert glucose["severity"] == "normal"
    assert data["overall_status"] in {"normal", "info"}


@pytest.mark.asyncio
async def test_insights_warning_measurements(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-warning@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=150,
        glucose_context="post_meal",
        systolic_pressure=130,
        diastolic_pressure=75,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "warning"
    assert len(data["alerts"]) >= 1
    assert len(data["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_insights_urgent_measurements(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-urgent@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=200,
        glucose_context="fasting",
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    glucose = _glucose_insight(data)
    assert glucose["severity"] == "urgent"
    assert data["overall_status"] == "urgent"
    assert any(alert["severity"] == "urgent" for alert in data["alerts"])
    assert "Prompt professional evaluation" in data["recommendations"][0]["message"]


@pytest.mark.asyncio
async def test_insights_glucose_context_affects_thresholds(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-glucose-context@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=130,
        glucose_context="post_meal",
    )

    post_meal = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert _glucose_insight(post_meal.json())["severity"] == "normal"

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-11T08:00:00Z",
        blood_glucose=130,
        glucose_context="fasting",
    )

    fasting = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert _glucose_insight(fasting.json())["severity"] == "urgent"


@pytest.mark.asyncio
async def test_insights_empty_history(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-empty@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}&{INSIGHTS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "info"
    assert data["alerts"] == []
    assert len(data["recommendations"]) == 1
    assert "Add more health measurements" in data["recommendations"][0]["message"]


@pytest.mark.asyncio
async def test_insights_date_filter(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-date-filter@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=200,
        glucose_context="fasting",
    )
    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-20T08:00:00Z",
        blood_glucose=95,
        glucose_context="fasting",
    )

    filtered = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}"
        "&date_from=2026-08-20T00:00:00Z&date_to=2026-08-20T23:59:59Z",
        headers=headers,
    )
    assert _glucose_insight(filtered.json())["severity"] == "normal"


@pytest.mark.asyncio
async def test_insights_requires_patient_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-no-patient@example.com")

    response = await client.get(
        "/api/v1/health-measurements/analytics/insights",
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_insights_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health-measurements/analytics/insights"
        "?patient_id=00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_insights_foreign_patient_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="hmi-owner@example.com")
    other_headers = await _register_and_login(client, email="hmi-other@example.com")
    patient_id = await _create_patient(client, owner_headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/insights?patient_id={patient_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_insights_nonexistent_patient_returns_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hmi-missing-patient@example.com")

    response = await client.get(
        "/api/v1/health-measurements/analytics/insights"
        "?patient_id=00000000-0000-0000-0000-000000000001",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"
