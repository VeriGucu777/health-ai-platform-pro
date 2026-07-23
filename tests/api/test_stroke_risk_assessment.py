"""Stroke risk assessment endpoint integration tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.reference_ranges import STROKE_RISK_DISCLAIMER
from tests.support.risk_assessment_test_helpers import (
    ASSESSMENT_DATE_RANGE,
    create_measurement,
    create_patient,
    register_and_login,
)


def _assessment_url(patient_id: str, *, date_range: str = ASSESSMENT_DATE_RANGE) -> str:
    return f"/api/v1/patients/{patient_id}/risk-assessments/stroke?{date_range}"


@pytest.mark.asyncio
async def test_assessment_returns_structured_response(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-structure@example.com")
    patient_id = await create_patient(client, headers)

    await create_measurement(
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
    assert data["model_version"] == "stroke_rule_based_v1"
    assert data["assessment_status"] == "completed"
    assert data["risk_level"] in {"low", "moderate", "elevated"}
    assert data["score"] is not None
    assert data["probability"] is None
    assert data["disclaimer"] == STROKE_RISK_DISCLAIMER


@pytest.mark.asyncio
async def test_assessment_low_risk(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-low@example.com")
    patient_id = await create_patient(client, headers)

    await create_measurement(
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
    assert response.status_code == 200
    assert response.json()["risk_level"] == "low"


@pytest.mark.asyncio
async def test_assessment_moderate_risk(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-moderate@example.com")
    patient_id = await create_patient(client, headers)

    await create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=110,
        glucose_context="fasting",
        systolic_pressure=128,
        diastolic_pressure=82,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert response.json()["risk_level"] == "moderate"


@pytest.mark.asyncio
async def test_assessment_elevated_risk(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-elevated@example.com")
    patient_id = await create_patient(client, headers)
    await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"date_of_birth": "1954-05-15"},
        headers=headers,
    )

    await create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=130,
        glucose_context="fasting",
        systolic_pressure=145,
        diastolic_pressure=92,
    )
    record_response = await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": "2026-08-09T10:00:00Z",
            "record_type": "stroke_history",
            "title": "Prior event documentation",
            "notes": "Free text must not be parsed",
        },
        headers=headers,
    )
    assert record_response.status_code == 201

    response = await client.get(_assessment_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert response.json()["risk_level"] == "elevated"


@pytest.mark.asyncio
async def test_assessment_insufficient_data_without_glucose(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-insufficient@example.com")
    patient_id = await create_patient(client, headers)

    await create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        systolic_pressure=118,
        diastolic_pressure=76,
    )

    response = await client.get(_assessment_url(patient_id), headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["assessment_status"] == "insufficient_data"
    assert data["risk_level"] is None
    assert data["score"] is None
    assert any(item["input"] == "blood_glucose" for item in data["missing_inputs"])


@pytest.mark.asyncio
async def test_assessment_requires_authentication(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-auth@example.com")
    patient_id = await create_patient(client, headers)

    response = await client.get(_assessment_url(patient_id))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_assessment_foreign_patient_not_found(client: AsyncClient) -> None:
    owner_headers = await register_and_login(client, email="sra-owner@example.com")
    other_headers = await register_and_login(client, email="sra-other@example.com")
    patient_id = await create_patient(client, owner_headers)

    response = await client.get(_assessment_url(patient_id), headers=other_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_assessment_nonexistent_patient_not_found(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-missing@example.com")

    response = await client.get(_assessment_url(str(uuid4())), headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assessment_invalid_date_range(client: AsyncClient) -> None:
    headers = await register_and_login(client, email="sra-invalid-range@example.com")
    patient_id = await create_patient(client, headers)

    response = await client.get(
        _assessment_url(
            patient_id,
            date_range="date_from=2026-08-31T00:00:00Z&date_to=2026-08-01T00:00:00Z",
        ),
        headers=headers,
    )
    assert response.status_code == 422
