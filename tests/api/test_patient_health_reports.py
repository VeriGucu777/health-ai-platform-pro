"""Patient health PDF report endpoint integration tests."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.support.pdf_report_helpers import (
    assert_disclaimers_present,
    assert_english_content_present,
    assert_turkish_content_present,
    extract_pdf_text,
    normalize_pdf_text,
)

REPORT_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    first_name: str = "Test",
    last_name: str = "User",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": first_name,
            "last_name": last_name,
            "role": "doctor",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    first_name: str = "John",
    last_name: str = "Doe",
) -> str:
    response = await client.post(
        "/api/v1/patients",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": "1990-05-15",
            "gender": "male",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _pdf_text(content: bytes) -> str:
    return extract_pdf_text(content)


def _report_url(patient_id: str, *, date_range: str = REPORT_DATE_RANGE) -> str:
    return f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{date_range}"


@pytest.mark.asyncio
async def test_generate_report_returns_valid_pdf(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-valid@example.com")
    patient_id = await _create_patient(
        client,
        headers,
        first_name="Şahin",
        last_name="Öğüt",
    )

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert f'patient-health-report-{patient_id}.pdf' in response.headers["content-disposition"]

    assert_turkish_content_present(response.content, _pdf_text(response.content))
    assert_english_content_present(_pdf_text(response.content))
    assert_disclaimers_present(response.content)


@pytest.mark.asyncio
async def test_generate_report_empty_history(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-empty@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Seçilen dönemde tıbbi kayıt bulunmamaktadır." in text
    assert "Add more health measurements over time" in text


@pytest.mark.asyncio
async def test_generate_report_date_filter(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-date-filter@example.com")
    patient_id = await _create_patient(client, headers)

    in_range = {
        "patient_id": patient_id,
        "measured_at": "2026-08-10T08:00:00Z",
        "blood_glucose": 200,
        "glucose_context": "fasting",
    }
    out_of_range = {
        "patient_id": patient_id,
        "measured_at": "2026-07-01T08:00:00Z",
        "blood_glucose": 90,
        "glucose_context": "fasting",
    }
    await client.post("/api/v1/health-measurements", json=in_range, headers=headers)
    await client.post("/api/v1/health-measurements", json=out_of_range, headers=headers)

    response = await client.get(
        _report_url(
            patient_id,
            date_range="date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z",
        ),
        headers=headers,
    )
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Prompt professional evaluation" in text


@pytest.mark.asyncio
async def test_generate_report_medical_record_limit_notice(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-record-limit@example.com")
    patient_id = await _create_patient(client, headers)

    for index in range(101):
        record_date = date(2026, 6, 1) + timedelta(days=index)
        payload = {
            "patient_id": patient_id,
            "record_date": f"{record_date.isoformat()}T10:00:00Z",
            "record_type": "visit",
            "title": f"Record {index + 1}",
        }
        response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        _report_url(
            patient_id,
            date_range="date_from=2026-06-01T00:00:00Z&date_to=2026-09-15T23:59:59Z",
        ),
        headers=headers,
    )
    assert response.status_code == 200
    text = normalize_pdf_text(_pdf_text(response.content))
    assert "en yeni 100 t" in text
    assert "101" in text


@pytest.mark.asyncio
async def test_generate_report_requires_authentication(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-auth@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(_report_url(patient_id))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_report_foreign_patient_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="phr-owner@example.com")
    other_headers = await _register_and_login(client, email="phr-other@example.com")
    patient_id = await _create_patient(client, owner_headers)

    response = await client.get(_report_url(patient_id), headers=other_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_generate_report_nonexistent_patient_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-missing@example.com")

    response = await client.get(
        "/api/v1/patients/00000000-0000-0000-0000-000000000001/reports/health-summary.pdf",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_generate_report_invalid_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-invalid-range@example.com")
    patient_id = await _create_patient(client, headers)

    response = await client.get(
        _report_url(
            patient_id,
            date_range="date_from=2026-08-20T00:00:00Z&date_to=2026-08-01T00:00:00Z",
        ),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_report_includes_alerts_and_recommendations(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="phr-alerts@example.com")
    patient_id = await _create_patient(client, headers)

    await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_id,
            "measured_at": "2026-08-10T08:00:00Z",
            "blood_glucose": 200,
            "glucose_context": "fasting",
            "systolic_pressure": 130,
            "diastolic_pressure": 75,
        },
        headers=headers,
    )

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Uyarılar" in text
    assert "Takip Önerileri" in text
    assert "Prompt professional evaluation" in text
