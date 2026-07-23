"""Diabetes risk assessment endpoint integration tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.reference_ranges import DIABETES_RISK_DISCLAIMER

ASSESSMENT_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"

PATIENT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
}


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
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
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

    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 201


def _assessment_url(patient_id: str, *, date_range: str = ASSESSMENT_DATE_RANGE) -> str:
    return f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{date_range}"


@pytest.mark.asyncio
async def test_assessment_returns_structured_response(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-structure@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=95,
        glucose_context="fasting",
        systolic_pressure=118,
        diastolic_pressure=76,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["patient_id"] == patient_id
    assert data["model_version"] == "rule_based_v1"
    assert data["assessment_status"] == "completed"
    assert data["risk_level"] in {"low", "moderate", "elevated"}
    assert data["score"] is not None
    assert data["probability"] is None
    assert len(data["contributing_factors"]) >= 1
    assert len(data["missing_inputs"]) >= 1
    assert data["disclaimer"] == DIABETES_RISK_DISCLAIMER
    assert "not a medical diagnosis" in data["disclaimer"]


@pytest.mark.asyncio
async def test_assessment_low_risk(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-low@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=92,
        glucose_context="fasting",
        systolic_pressure=110,
        diastolic_pressure=70,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    data = response.json()
    assert response.status_code == 200
    assert data["risk_level"] == "low"


@pytest.mark.asyncio
async def test_assessment_moderate_risk(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-moderate@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=110,
        glucose_context="fasting",
        systolic_pressure=118,
        diastolic_pressure=76,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    data = response.json()
    assert response.status_code == 200
    assert data["risk_level"] == "moderate"


@pytest.mark.asyncio
async def test_assessment_elevated_risk(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-elevated@example.com")
    patient_id = await _create_patient(
        client,
        headers,
    )
    await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"date_of_birth": "1960-05-15"},
        headers=headers,
    )

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=130,
        glucose_context="fasting",
        systolic_pressure=132,
        diastolic_pressure=84,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    data = response.json()
    assert response.status_code == 200
    assert data["risk_level"] == "elevated"


@pytest.mark.asyncio
async def test_assessment_insufficient_data_without_glucose(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-insufficient@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(_assessment_url(patient_id), headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["assessment_status"] == "insufficient_data"
    assert data["risk_level"] is None
    assert data["score"] is None
    assert data["probability"] is None
    assert any(item["input"] == "blood_glucose" for item in data["missing_inputs"])


@pytest.mark.asyncio
async def test_assessment_includes_structured_medical_record_factor(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-record@example.com")
    patient_id = await _create_patient(client, headers)

    await _create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=95,
        glucose_context="fasting",
        systolic_pressure=118,
        diastolic_pressure=76,
    )
    record_response = await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": "2026-08-09T10:00:00Z",
            "record_type": "lab_result",
            "title": "Glucose Panel",
            "diagnosis": "Should not be parsed",
        },
        headers=headers,
    )
    assert record_response.status_code == 201

    response = await client.get(_assessment_url(patient_id), headers=headers)
    data = response.json()
    assert response.status_code == 200
    assert any(
        factor["source"] == "medical_record" and "lab_result" in factor["message"]
        for factor in data["contributing_factors"]
    )
    assert all("Should not be parsed" not in factor["message"] for factor in data["contributing_factors"])


@pytest.mark.asyncio
async def test_assessment_requires_authentication(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-auth@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(_assessment_url(patient_id))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_assessment_foreign_patient_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="dra-owner@example.com")
    other_headers = await _register_and_login(client, email="dra-other@example.com")
    patient_id = await _create_patient(client, owner_headers)

    response = await client.get(_assessment_url(patient_id), headers=other_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_assessment_nonexistent_patient_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-missing@example.com")

    response = await client.get(
        _assessment_url(str(uuid4())),
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_assessment_invalid_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="dra-invalid-range@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        _assessment_url(
            patient_id,
            date_range="date_from=2026-08-31T00:00:00Z&date_to=2026-08-01T00:00:00Z",
        ),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["message"] == "date_from must be before or equal to date_to"
