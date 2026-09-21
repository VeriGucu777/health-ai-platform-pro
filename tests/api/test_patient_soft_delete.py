"""Patient soft delete (deactivate) and inactive patient access."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.api.test_patients import PATIENT_PAYLOAD, _register_and_login


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_clinic_admin(user_repository, email: str) -> User:
    return await user_repository.create(
        User(
            email=email,
            hashed_password=hash_password("securepass123"),
            first_name="Clinic",
            last_name="Admin",
            role=UserRole.CLINIC_ADMIN,
        ),
    )


async def _seed_doctor(user_repository, email: str) -> User:
    return await user_repository.create(
        User(
            email=email,
            hashed_password=hash_password("securepass123"),
            first_name="Doc",
            last_name="Tor",
            role=UserRole.DOCTOR,
        ),
    )


def _patient(*, owner_id, organization_id) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Soft",
        last_name="Delete",
        date_of_birth=date(1990, 1, 1),
        gender="male",
    )


@pytest.mark.asyncio
async def test_clinic_admin_delete_deactivates_patient_row_preserved(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
    medical_record_repository,
    audit_log_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "soft-ca@example.com")
    owner = await _seed_doctor(user_repository, "soft-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=owner.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await medical_record_repository.create(
        MedicalRecord(
            patient_id=patient.id,
            owner_id=owner.id,
            record_type="note",
            title="Keep after soft delete",
            description="clinical history",
            record_date=datetime.now(UTC),
        ),
    )
    headers = await _login(client, admin.email)
    audit_log_repository.records.clear()

    response = await client.delete(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 204

    stored = await patient_repository.get_by_id(patient.id)
    assert stored is not None
    assert stored.is_active is False
    assert stored.organization_id == org_id
    assert stored.owner_id == owner.id
    assignments = await assignment_repository.list_by_patient_and_organization(
        patient.id,
        org_id,
    )
    assert len(assignments) >= 1
    assert len(await medical_record_repository.list_all()) == 1
    assert len(audit_log_repository.list_all()) >= 1


@pytest.mark.asyncio
async def test_assigned_doctor_delete_deactivates(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "soft-del-owner@example.com")
    doctor = await _seed_doctor(user_repository, "soft-del-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    for uid in (owner.id, doctor.id):
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=uid,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=doctor.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    assert (await client.delete(f"/api/v1/patients/{patient.id}", headers=headers)).status_code == 204
    stored = await patient_repository.get_by_id(patient.id)
    assert stored is not None and stored.is_active is False


@pytest.mark.asyncio
async def test_inactive_patient_hidden_and_clinical_endpoints_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    medical_record_repository,
    health_measurement_repository,
    appointment_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "soft-inactive@example.com")
    owner = await _seed_doctor(user_repository, "soft-inactive-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    patient.is_active = False
    await patient_repository.update(patient)
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=owner.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)

    assert (await client.get("/api/v1/patients", headers=headers)).json()["total"] == 0
    assert (await client.get(f"/api/v1/patients/{patient.id}", headers=headers)).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/patients/{patient.id}",
            headers=headers,
            json={"first_name": "Nope"},
        )
    ).status_code == 404
    assert (await client.delete(f"/api/v1/patients/{patient.id}", headers=headers)).status_code == 404
    assert (
        await client.get(f"/api/v1/patients/{patient.id}/clinical-timeline", headers=headers)
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/patients/{patient.id}/risk-assessments/diabetes"
            "?date_from=2020-01-01T00:00:00Z&date_to=2030-01-01T00:00:00Z",
            headers=headers,
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/patients/{patient.id}/health-report/pdf"
            "?date_from=2020-01-01T00:00:00Z&date_to=2030-01-01T00:00:00Z",
            headers=headers,
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/patients/{patient.id}/assignments", headers=headers)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/patients/{patient.id}/consents", headers=headers)
    ).status_code == 404

    # Child rows untouched (not cascade deleted)
    assert await medical_record_repository.list_all() == []
    assert await health_measurement_repository.list_all() == []
    assert await appointment_repository.list_all() == []


@pytest.mark.asyncio
async def test_soft_deleted_patient_second_delete_returns_404(
    client: AsyncClient,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="soft-second-del@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = created.json()["id"]
    assert (await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_patient_request_schema_rejects_injected_fields(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="strict-schema@example.com")
    for payload in (
        {**PATIENT_PAYLOAD, "owner_id": str(uuid4())},
        {**PATIENT_PAYLOAD, "organization_id": str(uuid4())},
        {**PATIENT_PAYLOAD, "extra_field": "nope"},
    ):
        assert (await client.post("/api/v1/patients", json=payload, headers=headers)).status_code == 422

    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = created.json()["id"]
    assert (
        await client.patch(
            f"/api/v1/patients/{patient_id}",
            headers=headers,
            json={"owner_id": str(uuid4())},
        )
    ).status_code == 422
    assert (
        await client.patch(
            f"/api/v1/patients/{patient_id}",
            headers=headers,
            json={"organization_id": str(uuid4())},
        )
    ).status_code == 422
    assert (
        await client.patch(
            f"/api/v1/patients/{patient_id}",
            headers=headers,
            json={"is_active": False},
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_duplicate_consent_grant_failure_audit_has_organization_id(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "soft-consent-audit@example.com")
    owner = await _seed_doctor(user_repository, "soft-consent-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    grant_body = {"consent_type": "clinical_data_processing"}
    assert (
        await client.post(f"/api/v1/patients/{patient.id}/consents", headers=headers, json=grant_body)
    ).status_code == 201
    audit_log_repository.records.clear()
    dup = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json=grant_body,
    )
    assert dup.status_code == 409
    failures = [
        r
        for r in audit_log_repository.list_all()
        if r.resource_type == AuditResourceType.PATIENT_CONSENT
        and r.action == AuditAction.GRANT
        and r.outcome == AuditOutcome.FAILURE
    ]
    assert len(failures) == 1
    assert failures[0].organization_id == org_id
    assert failures[0].metadata == {"consent_type": "clinical_data_processing"}
    assert "Sensitive" not in str(failures[0].metadata)
