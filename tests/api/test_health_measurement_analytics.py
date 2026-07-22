"""Health measurement analytics endpoint integration tests."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

PATIENT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
}

ANALYTICS_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


async def _register_and_login(client: AsyncClient, *, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "role": "patient",
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
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
) -> None:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "measured_at": measured_at,
    }
    if blood_glucose is not None:
        payload["blood_glucose"] = blood_glucose
    if systolic_pressure is not None:
        payload["systolic_pressure"] = systolic_pressure
    if diastolic_pressure is not None:
        payload["diastolic_pressure"] = diastolic_pressure
    if heart_rate is not None:
        payload["heart_rate"] = heart_rate

    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_summary_returns_overall_statistics(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-summary@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=100,
        systolic_pressure=120,
        diastolic_pressure=80,
    )
    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-11T08:00:00Z",
        blood_glucose=120,
        systolic_pressure=130,
        diastolic_pressure=85,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["total_measurement_count"] == 2
    assert "disclaimer" in data
    assert "not a medical diagnosis" in data["disclaimer"]

    glucose = next(item for item in data["overall"] if item["metric"] == "blood_glucose")
    systolic = next(item for item in data["overall"] if item["metric"] == "systolic_pressure")
    diastolic = next(item for item in data["overall"] if item["metric"] == "diastolic_pressure")

    assert Decimal(glucose["average"]) == Decimal("110")
    assert Decimal(glucose["minimum"]) == Decimal("100")
    assert Decimal(glucose["maximum"]) == Decimal("120")
    assert glucose["measurement_count"] == 2
    assert Decimal(systolic["average"]) == Decimal("125")
    assert Decimal(diastolic["average"]) == Decimal("82.5")


@pytest.mark.asyncio
async def test_trends_returns_daily_periods(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-trends-daily@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=100,
    )
    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-11T08:00:00Z",
        blood_glucose=120,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/trends?patient_id={patient_id}&period=daily&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "daily"
    assert len(data["periods"]) == 2


@pytest.mark.asyncio
async def test_trends_weekly_and_monthly_periods(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-trends-periods@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=100,
    )
    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-20T08:00:00Z",
        blood_glucose=120,
    )

    weekly = await client.get(
        f"/api/v1/health-measurements/analytics/trends?patient_id={patient_id}&period=weekly&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    monthly = await client.get(
        f"/api/v1/health-measurements/analytics/trends?patient_id={patient_id}&period=monthly&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert weekly.status_code == 200
    assert monthly.status_code == 200
    assert len(weekly.json()["periods"]) >= 1
    assert len(monthly.json()["periods"]) == 1


@pytest.mark.asyncio
async def test_trends_metric_filter(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-metric-filter@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=100,
        heart_rate=70,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/trends?patient_id={patient_id}"
        f"&period=daily&metric=blood_glucose&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["overall"]) == 1
    assert data["overall"][0]["metric"] == "blood_glucose"


@pytest.mark.asyncio
async def test_trends_trend_directions(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-trend-direction@example.com")
    patient_id = await _create_patient(client, headers)

    for day, glucose in ((10, 100), (11, 110), (12, 120), (13, 130)):
        await _create_measurement(
            client,
            headers,
            patient_id=patient_id,
            measured_at=f"2026-08-{day}T08:00:00Z",
            blood_glucose=glucose,
        )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}"
        f"&metric=blood_glucose&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    glucose = response.json()["overall"][0]
    assert glucose["trend_direction"] == "increasing"


@pytest.mark.asyncio
async def test_summary_target_range_status(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-target-range@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=200,
    )

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}"
        f"&metric=blood_glucose&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["overall"][0]["target_range_status"] == "above_reference_range"


@pytest.mark.asyncio
async def test_summary_requires_patient_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-no-patient@example.com")

    response = await client.get(
        "/api/v1/health-measurements/analytics/summary",
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summary_invalid_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-invalid-range@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}"
        "&date_from=2026-08-20T00:00:00Z&date_to=2026-08-10T00:00:00Z",
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_summary_date_range_too_large(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-large-range@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}"
        "&date_from=2024-01-01T00:00:00Z&date_to=2026-01-01T00:00:00Z",
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["message"] == "Date range cannot exceed 366 days"


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health-measurements/analytics/summary"
        "?patient_id=00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_foreign_patient_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="hma-owner@example.com")
    other_headers = await _register_and_login(client, email="hma-other@example.com")
    patient_id = await _create_patient(client, owner_headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_nonexistent_patient_returns_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-missing-patient@example.com")

    response = await client.get(
        "/api/v1/health-measurements/analytics/summary"
        "?patient_id=00000000-0000-0000-0000-000000000001",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_empty_dataset_returns_zero_counts(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hma-empty@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        f"/api/v1/health-measurements/analytics/summary?patient_id={patient_id}&{ANALYTICS_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_measurement_count"] == 0
    glucose = next(item for item in data["overall"] if item["metric"] == "blood_glucose")
    assert glucose["measurement_count"] == 0
    assert glucose["trend_direction"] == "insufficient_data"
