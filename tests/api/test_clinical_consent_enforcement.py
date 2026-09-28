"""CLINICAL_CONSENT_ENFORCED feature flag behavior."""

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from tests.api.test_patient_consents import _login, _seed_org_context
from tests.support.org_assigned_patient_harness import (
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
)


@pytest.mark.asyncio
async def test_flag_off_allows_clinical_without_consent(
    client: AsyncClient,
    test_settings: Settings,
    user_repository,
    membership_repository,
) -> None:
    test_settings.clinical_consent_enforced = False
    headers = await register_and_login_doctor(client, email="consent-off-doc@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    response = await client.get(
        "/api/v1/health-measurements",
        params={"patient_id": patient_id},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_flag_on_denies_without_consent(
    client: AsyncClient,
    test_settings: Settings,
    user_repository,
    membership_repository,
) -> None:
    test_settings.clinical_consent_enforced = True
    headers = await register_and_login_doctor(client, email="consent-deny-doc@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    response = await client.get(
        "/api/v1/health-measurements",
        params={"patient_id": patient_id},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["details"]["reason_code"] == "consent_required"


@pytest.mark.asyncio
async def test_flag_on_allows_with_active_consent(
    client: AsyncClient,
    test_settings: Settings,
    user_repository,
    membership_repository,
) -> None:
    test_settings.clinical_consent_enforced = True
    doctor_headers = await register_and_login_doctor(client, email="consent-allow-doc@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        doctor_headers,
    )
    admin_email = f"harness-ca-consent-allow-doc@example.com"
    admin_headers = await _login(client, admin_email)
    grant = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=admin_headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert grant.status_code == 201
    response = await client.get(
        "/api/v1/health-measurements",
        params={"patient_id": patient_id},
        headers=doctor_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_consent_admin_grant_not_blocked_when_clinical_gate_on(
    client: AsyncClient,
    test_settings: Settings,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    test_settings.clinical_consent_enforced = True
    _org_id, _admin, patient, _cross, _legacy = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    admin_headers = await _login(client, "consent-admin@example.com")
    grant = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=admin_headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert grant.status_code == 201
