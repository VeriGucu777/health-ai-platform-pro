"""Clinic admin patient consent management."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from app.domain.consent.enums import ConsentStatus, ConsentType
from app.domain.consent.entities import PatientConsent
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole


def _patient(*, owner_id, organization_id) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Consent",
        last_name="Patient",
        date_of_birth=date(1990, 5, 5),
        gender="female",
    )


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_user(user_repository, email: str, role: UserRole) -> User:
    return await user_repository.create(
        User(
            email=email,
            hashed_password=hash_password("securepass123"),
            first_name="Test",
            last_name="User",
            role=role,
        ),
    )


async def _seed_org_context(
    *,
    user_repository,
    patient_repository,
    membership_repository,
):
    org_id = uuid4()
    owner = await _seed_user(user_repository, "consent-owner@example.com", UserRole.DOCTOR)
    admin = await _seed_user(user_repository, "consent-admin@example.com", UserRole.CLINIC_ADMIN)
    outsider = await _seed_user(user_repository, "consent-outsider@example.com", UserRole.DOCTOR)

    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))

    for user_id, role in [
        (owner.id, OrganizationMembershipRole.DOCTOR),
        (admin.id, OrganizationMembershipRole.CLINIC_ADMIN),
    ]:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=role,
                status=MembershipStatus.ACTIVE,
            ),
        )

    org_b = uuid4()
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_b,
            user_id=outsider.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    cross_patient = await patient_repository.create(
        _patient(owner_id=outsider.id, organization_id=org_b),
    )

    legacy_patient = await patient_repository.create(
        Patient(
            owner_id=owner.id,
            organization_id=None,
            first_name="Legacy",
            last_name="Patient",
            date_of_birth=date(1988, 1, 1),
            gender="male",
        ),
    )

    return org_id, admin, patient, cross_patient, legacy_patient


@pytest.mark.asyncio
async def test_clinic_admin_grants_consent(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    _, admin, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "granted"
    assert body["version"] == 1
    assert body["recorded_by_user_id"] == str(admin.id)

    audits = audit_log_repository.list_all()
    grant_audits = [
        a
        for a in audits
        if a.resource_type == AuditResourceType.PATIENT_CONSENT and a.action == AuditAction.GRANT
    ]
    assert grant_audits
    meta = grant_audits[-1].metadata or {}
    assert meta.get("consent_type") == "clinical_data_processing"
    assert "first_name" not in meta and "email" not in meta


@pytest.mark.asyncio
async def test_duplicate_active_consent_returns_conflict(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    consent_repository,
) -> None:
    org_id, admin, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    await consent_repository.create(
        PatientConsent(
            patient_id=patient.id,
            organization_id=org_id,
            consent_type=ConsentType.CLINICAL_DATA_PROCESSING,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.now(UTC),
            recorded_by_user_id=admin.id,
            version=1,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_revoke_and_regrant_preserves_history(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    consent_repository,
    audit_log_repository,
) -> None:
    _, admin, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    headers = await _login(client, admin.email)
    grant = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    consent_id = grant.json()["id"]

    revoke = await client.patch(
        f"/api/v1/patients/{patient.id}/consents/{consent_id}",
        headers=headers,
    )
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"
    assert revoke.json()["revoked_at"] is not None

    regrant = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert regrant.status_code == 201
    assert regrant.json()["version"] == 2

    history = await client.get(f"/api/v1/patients/{patient.id}/consents", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["items"]) == 2
    statuses = {row.status for row in consent_repository.list_all()}
    assert ConsentStatus.GRANTED in statuses and ConsentStatus.REVOKED in statuses

    revoke_audits = [
        a
        for a in audit_log_repository.list_all()
        if a.resource_type == AuditResourceType.PATIENT_CONSENT and a.action == AuditAction.REVOKE
    ]
    view_audits = [
        a
        for a in audit_log_repository.list_all()
        if a.resource_type == AuditResourceType.PATIENT_CONSENT and a.action == AuditAction.VIEW
    ]
    assert revoke_audits and view_audits


@pytest.mark.asyncio
async def test_cross_org_patient_consent_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    _, admin, _, cross_patient, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    headers = await _login(client, admin.email)
    assert (
        await client.get(f"/api/v1/patients/{cross_patient.id}/consents", headers=headers)
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/patients/{cross_patient.id}/consents",
            headers=headers,
            json={"consent_type": "clinical_data_processing"},
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_legacy_org_null_patient_not_auto_granted(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    consent_repository,
) -> None:
    _, admin, _, _, legacy_patient = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{legacy_patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert response.status_code == 404
    assert consent_repository.list_all() == []


@pytest.mark.asyncio
async def test_non_clinic_admin_roles_forbidden(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    _, admin, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    doctor = await _seed_user(user_repository, "consent-doctor@example.com", UserRole.DOCTOR)
    patient_user = await _seed_user(user_repository, "consent-patient-user@example.com", UserRole.PATIENT)
    system_admin = await _seed_user(user_repository, "consent-sys@example.com", UserRole.SYSTEM_ADMIN)

    for email in (doctor.email, patient_user.email, system_admin.email):
        headers = await _login(client, email)
        assert (
            await client.get(f"/api/v1/patients/{patient.id}/consents", headers=headers)
        ).status_code == 403


@pytest.mark.asyncio
async def test_consent_history_not_removed_after_revoke(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    consent_repository,
) -> None:
    _, admin, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
    )
    headers = await _login(client, admin.email)
    grant = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    consent_id = grant.json()["id"]
    await client.patch(f"/api/v1/patients/{patient.id}/consents/{consent_id}", headers=headers)
    assert len(consent_repository.list_all()) == 1
    assert consent_repository.list_all()[0].status == ConsentStatus.REVOKED
