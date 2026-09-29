"""Patient health PDF report endpoint integration tests."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.domain.organization.enums import OrganizationMembershipRole
from tests.api.test_child_resource_policy import _login, _membership, _seed_clinic_admin
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
    user_repository,
    membership_repository,
    *,
    doctor_email: str,
    first_name: str = "John",
    last_name: str = "Doe",
    date_of_birth: str = "1990-05-15",
    gender: str = "male",
    notes: str | None = None,
    extra_org_doctor_emails: tuple[str, ...] = (),
) -> str:
    """Clinic admin creates org patient and assigns the doctor (doctors cannot POST /patients)."""
    doctor = await user_repository.get_by_email(doctor_email)
    assert doctor is not None
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, f"phr-ca-{doctor_email}")
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=doctor.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    for peer_email in extra_org_doctor_emails:
        peer = await user_repository.get_by_email(peer_email)
        assert peer is not None
        await _membership(
            membership_repository,
            org_id=org_id,
            user_id=peer.id,
            role=OrganizationMembershipRole.DOCTOR,
        )
    admin_headers = await _login(client, admin.email)
    patient_payload: dict[str, str] = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth,
        "gender": gender,
    }
    if notes is not None:
        patient_payload["notes"] = notes
    create = await client.post(
        "/api/v1/patients",
        json=patient_payload,
        headers=admin_headers,
    )
    assert create.status_code == 201
    patient_id = create.json()["id"]
    assign = await client.post(
        f"/api/v1/patients/{patient_id}/assignments",
        headers=admin_headers,
        json={"assignee_user_id": str(doctor.id), "is_primary": False},
    )
    assert assign.status_code == 201
    return patient_id


def _pdf_text(content: bytes) -> str:
    return extract_pdf_text(content)


def _report_url(
    patient_id: str,
    *,
    date_range: str = REPORT_DATE_RANGE,
    locale: str | None = None,
) -> str:
    suffix = date_range
    if locale:
        suffix = f"{date_range}&locale={locale}"
    return f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{suffix}"


@pytest.mark.asyncio
async def test_generate_report_returns_valid_pdf(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-valid@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        first_name="Şahin",
        last_name="Öğüt",
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert f'patient-health-report-{patient_id}.pdf' in response.headers["content-disposition"]

    text = _pdf_text(response.content)
    assert_turkish_content_present(response.content, text)
    assert "Hasta Sağlık Raporu" in text
    assert_disclaimers_present(response.content, locale="tr")

    response_en = await client.get(_report_url(patient_id, locale="en"), headers=headers)
    assert response_en.status_code == 200
    assert_english_content_present(_pdf_text(response_en.content))
    assert_disclaimers_present(response_en.content, locale="en")


@pytest.mark.asyncio
async def test_generate_report_empty_history(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-empty@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Seçilen dönemde tıbbi kayıt bulunmamaktadır." in text
    assert "Anlamlı içgörüler için" in text
    assert "Add more health measurements over time" not in text


@pytest.mark.asyncio
async def test_generate_report_date_filter(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-date-filter@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

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
            locale="en",
        ),
        headers=headers,
    )
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Prompt professional evaluation" in text


@pytest.mark.asyncio
async def test_generate_report_medical_record_limit_notice(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-record-limit@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

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
            locale="tr",
        ),
        headers=headers,
    )
    assert response.status_code == 200
    text = normalize_pdf_text(_pdf_text(response.content))
    assert "en yeni 100 t" in text
    assert "101" in text


@pytest.mark.asyncio
async def test_generate_report_requires_authentication(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-auth@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_report_foreign_patient_not_found(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_email = "phr-owner@example.com"
    other_email = "phr-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)
    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        doctor_email=owner_email,
        extra_org_doctor_emails=(other_email,),
    )

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
async def test_generate_report_invalid_date_range(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-invalid-range@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(
        _report_url(
            patient_id,
            date_range="date_from=2026-08-20T00:00:00Z&date_to=2026-08-01T00:00:00Z",
        ),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_report_includes_alerts_and_recommendations(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-alerts@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _create_patient(
        client, user_repository, membership_repository, doctor_email=email
    )

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

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Uyarılar" in text
    assert "Takip önerileri" in text
    assert "profesyonel değerlendirme" in text.lower()
