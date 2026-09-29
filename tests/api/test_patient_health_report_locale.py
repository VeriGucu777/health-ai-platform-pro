"""PDF locale acceptance and security behavior via HTTP (observable outcomes)."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.support.pdf_locale_acceptance import (
    assert_english_date_style_present,
    assert_english_pdf_meets_locale_acceptance,
    assert_pdf_text_differs_by_locale,
    assert_turkish_date_style_present,
    assert_turkish_pdf_meets_locale_acceptance,
    verify_english_pdf_output,
    verify_turkish_pdf_output,
)
from tests.api.test_patient_health_reports import (
    REPORT_DATE_RANGE,
    _create_patient,
    _register_and_login,
)
from tests.support.pdf_report_helpers import extract_pdf_text

SAMPLE_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "tmp" / "pdf_locale_samples"

_LOCALE_PATIENT = {
    "first_name": "Locale",
    "last_name": "Patient",
    "gender": "female",
}


async def _locale_patient_id(
    client: AsyncClient,
    user_repository,
    membership_repository,
    *,
    doctor_email: str,
    notes: str | None = None,
) -> str:
    return await _create_patient(
        client,
        user_repository,
        membership_repository,
        doctor_email=doctor_email,
        notes=notes,
        **_LOCALE_PATIENT,
    )


def _report_url(patient_id: str, *, locale: str | None = None) -> str:
    query = REPORT_DATE_RANGE
    if locale is not None:
        query = f"{query}&locale={locale}"
    return f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{query}"


@pytest.mark.asyncio
async def test_pdf_without_locale_defaults_to_english_acceptance(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-default@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert_english_pdf_meets_locale_acceptance(text)
    assert_english_date_style_present(text)


@pytest.mark.asyncio
async def test_pdf_locale_tr_meets_turkish_acceptance(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-tr@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert_turkish_pdf_meets_locale_acceptance(text)
    assert_turkish_date_style_present(text)


@pytest.mark.asyncio
async def test_pdf_locale_en_meets_english_acceptance(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-en@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="en"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert_english_pdf_meets_locale_acceptance(text)


@pytest.mark.asyncio
async def test_pdf_locale_tr_and_en_produce_different_content(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-diff@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    tr_response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    en_response = await client.get(_report_url(patient_id, locale="en"), headers=headers)
    assert tr_response.status_code == 200
    assert en_response.status_code == 200
    assert_pdf_text_differs_by_locale(
        extract_pdf_text(tr_response.content),
        extract_pdf_text(en_response.content),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_locale", ["de", "fr", "tr-TR", ""])
async def test_pdf_unsupported_locale_falls_back_to_english(
    client: AsyncClient,
    user_repository,
    membership_repository,
    invalid_locale: str,
) -> None:
    email = f"phr-locale-invalid-{invalid_locale or 'empty'}@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale=invalid_locale), headers=headers)
    assert response.status_code == 200
    assert_english_pdf_meets_locale_acceptance(extract_pdf_text(response.content))


@pytest.mark.asyncio
async def test_pdf_locale_tr_case_insensitive(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-tr-case@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="TR"), headers=headers)
    assert response.status_code == 200
    assert_turkish_pdf_meets_locale_acceptance(extract_pdf_text(response.content))


@pytest.mark.asyncio
async def test_pdf_seed_prefixed_notes_never_appear_in_output(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-seed@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        notes="seed:demo-live-policy-patient-v1",
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content).lower()
    assert "seed:" not in text
    assert "demo-live-policy" not in text


@pytest.mark.asyncio
async def test_pdf_shows_clinical_notes_but_not_seed_prefix(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-clinical-note@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        notes="Alerji: penisilin",
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert "Alerji: penisilin" in text


@pytest.mark.asyncio
async def test_pdf_locale_does_not_bypass_authentication(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-auth@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="tr"))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pdf_locale_does_not_bypass_invalid_token(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-bad-token@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(
        _report_url(patient_id, locale="tr"),
        headers={"Authorization": "Bearer not.a.valid.jwt"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pdf_locale_does_not_bypass_cross_user_access(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_email = "phr-locale-owner@example.com"
    other_email = "phr-locale-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)
    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        doctor_email=owner_email,
        extra_org_doctor_emails=(other_email,),
        **_LOCALE_PATIENT,
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=other_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_pdf_locale_tr_localizes_patient_enums(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-enums@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        notes="Alerji: yok",
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert "Kadın" in text
    assert "Aktif" in text
    assert "female" not in text.lower()
    assert "| info |" not in text.lower()


@pytest.mark.asyncio
async def test_end_to_end_locale_pdf_verification_samples(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    """Same demo patient: TR/EN PDF bytes + product verification flags (acceptance gate)."""
    email = "phr-locale-e2e-sample@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        notes="seed:demo-live-policy-patient-v1",
    )
    await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_id,
            "measured_at": "2026-08-10T08:00:00Z",
            "blood_glucose": 200,
            "glucose_context": "fasting",
        },
        headers=headers,
    )

    tr_resp = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    en_resp = await client.get(_report_url(patient_id, locale="en"), headers=headers)
    assert tr_resp.status_code == 200
    assert en_resp.status_code == 200

    tr_text = extract_pdf_text(tr_resp.content)
    en_text = extract_pdf_text(en_resp.content)
    assert tr_resp.headers.get("X-Report-Locale") == "tr"
    assert en_resp.headers.get("X-Report-Locale") == "en"

    tr_flags = verify_turkish_pdf_output(tr_text)
    en_flags = verify_english_pdf_output(en_text)

    assert tr_flags["english_leakage"] == "NO", tr_flags.get("english_leak_phrases")
    assert tr_flags["internal_marker_leakage"] == "NO"
    assert tr_flags["enum_localized"] == "YES"
    assert tr_flags["date_localized"] == "YES"
    assert en_flags == {
        "turkish_leakage": "NO",
        "internal_marker_leakage": "NO",
        "enum_localized": "YES",
        "date_localized": "YES",
    }

    SAMPLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tr_path = SAMPLE_OUTPUT_DIR / f"patient-{patient_id}-tr.pdf"
    en_path = SAMPLE_OUTPUT_DIR / f"patient-{patient_id}-en.pdf"
    tr_path.write_bytes(tr_resp.content)
    en_path.write_bytes(en_resp.content)
    manifest = {
        "patient_id": patient_id,
        "tr_pdf": str(tr_path),
        "en_pdf": str(en_path),
        "tr_verification": tr_flags,
        "en_verification": en_flags,
    }
    (SAMPLE_OUTPUT_DIR / "latest-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (SAMPLE_OUTPUT_DIR / "latest-tr-extract.txt").write_text(tr_text, encoding="utf-8")
    (SAMPLE_OUTPUT_DIR / "latest-en-extract.txt").write_text(en_text, encoding="utf-8")


@pytest.mark.asyncio
async def test_pdf_turkish_via_accept_language_when_locale_query_omitted(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-accept@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )
    headers_with_lang = {
        **headers,
        "Accept-Language": "tr-TR,tr;q=0.9",
    }

    response = await client.get(
        f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{REPORT_DATE_RANGE}",
        headers=headers_with_lang,
    )
    assert response.status_code == 200
    assert response.headers.get("X-Report-Locale") == "tr"
    assert_turkish_pdf_meets_locale_acceptance(extract_pdf_text(response.content))


@pytest.mark.asyncio
async def test_pdf_empty_history_tr_has_no_english_empty_state_leak(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    email = "phr-locale-empty-tr@example.com"
    headers = await _register_and_login(client, email=email)
    patient_id = await _locale_patient_id(
        client, user_repository, membership_repository, doctor_email=email
    )

    response = await client.get(_report_url(patient_id, locale="tr"), headers=headers)
    assert response.status_code == 200
    text = extract_pdf_text(response.content)
    assert "Add more health measurements over time" not in text
    assert "No blood glucose measurements were recorded" not in text
