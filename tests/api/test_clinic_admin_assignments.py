"""Clinic admin organization membership and patient assignment management."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole

ASSESSMENT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"
REPORT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


def _patient(*, owner_id, organization_id) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Assign",
        last_name="Patient",
        date_of_birth=date(1992, 1, 1),
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
    assignment_repository,
):
    org_id = uuid4()
    owner = await _seed_user(user_repository, "mgmt-owner@example.com", UserRole.DOCTOR)
    doctor_b = await _seed_user(user_repository, "mgmt-docb@example.com", UserRole.DOCTOR)
    admin = await _seed_user(user_repository, "mgmt-admin@example.com", UserRole.CLINIC_ADMIN)
    outsider = await _seed_user(user_repository, "mgmt-outsider@example.com", UserRole.DOCTOR)

    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))

    for user_id, role in [
        (owner.id, OrganizationMembershipRole.DOCTOR),
        (doctor_b.id, OrganizationMembershipRole.DOCTOR),
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

    return org_id, admin, doctor_b, patient, outsider, cross_patient


@pytest.mark.asyncio
async def test_clinic_admin_lists_doctors(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id, admin, doctor_b, *_ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, admin.email)
    response = await client.get("/api/v1/organizations/me/members/doctors", headers=headers)
    assert response.status_code == 200
    user_ids = {item["user_id"] for item in response.json()["items"]}
    assert str(doctor_b.id) in user_ids


@pytest.mark.asyncio
async def test_clinic_admin_creates_assignment_and_doctor_gains_access(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
    audit_log_repository,
) -> None:
    _, admin, doctor_b, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    admin_headers = await _login(client, admin.email)
    doc_headers = await _login(client, doctor_b.email)

    assert (await client.get(f"/api/v1/patients/{patient.id}/clinical-timeline", headers=doc_headers)).status_code == 404

    create = await client.post(
        f"/api/v1/patients/{patient.id}/assignments",
        headers=admin_headers,
        json={"assignee_user_id": str(doctor_b.id), "is_primary": False},
    )
    assert create.status_code == 201
    assignment_id = create.json()["id"]
    assert create.json()["assigned_by_user_id"] == str(admin.id)

    assert (await client.get(f"/api/v1/patients/{patient.id}", headers=doc_headers)).status_code == 200
    assert (
        await client.get(f"/api/v1/patients/{patient.id}/clinical-timeline", headers=doc_headers)
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/patients/{patient.id}/risk-assessments/diabetes?{ASSESSMENT_RANGE}",
            headers=doc_headers,
        )
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/patients/{patient.id}/reports/health-summary.pdf?{REPORT_RANGE}",
            headers=doc_headers,
        )
    ).status_code == 200

    audits = audit_log_repository.list_all()
    create_audits = [
        a
        for a in audits
        if a.resource_type == AuditResourceType.PATIENT_ASSIGNMENT
        and a.action == AuditAction.CREATE
    ]
    assert create_audits
    meta = create_audits[-1].metadata or {}
    assert "email" not in meta and "first_name" not in meta
    assert meta.get("is_primary") is False
    assert create_audits[-1].organization_id is not None

    deactivate = await client.patch(
        f"/api/v1/patients/{patient.id}/assignments/{assignment_id}",
        headers=admin_headers,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["status"] == "inactive"
    assert deactivate.json()["ended_at"] is not None
    assert (
        await client.get(f"/api/v1/patients/{patient.id}/clinical-timeline", headers=doc_headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_duplicate_active_assignment_returns_conflict(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id, admin, doctor_b, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=doctor_b.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{patient.id}/assignments",
        headers=headers,
        json={"assignee_user_id": str(doctor_b.id)},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cross_org_doctor_assignment_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    _, admin, _, patient, outsider, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{patient.id}/assignments",
        headers=headers,
        json={"assignee_user_id": str(outsider.id)},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cross_org_patient_assignment_list_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    _, admin, _, _, _, cross_patient = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, admin.email)
    assert (
        await client.get(f"/api/v1/patients/{cross_patient.id}/assignments", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_doctor_cannot_use_management_endpoints(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "mgmt-doctor-only@example.com",
            "password": "securepass123",
            "first_name": "Doc",
            "last_name": "Only",
            "role": "doctor",
        },
    )
    headers = await _login(client, "mgmt-doctor-only@example.com")
    assert (await client.get("/api/v1/organizations/me/members/doctors", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_patient_and_system_admin_management_forbidden(
    client: AsyncClient,
    user_repository,
) -> None:
    patient = await _seed_user(user_repository, "mgmt-pat-role@example.com", UserRole.PATIENT)
    sys_admin = await _seed_user(user_repository, "mgmt-sys-role@example.com", UserRole.SYSTEM_ADMIN)
    for email in (patient.email, sys_admin.email):
        headers = await _login(client, email)
        assert (
            await client.get("/api/v1/organizations/me/membership", headers=headers)
        ).status_code == 403


@pytest.mark.asyncio
async def test_primary_assignment_conflict(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id, admin, doctor_b, patient, _, _ = await _seed_org_context(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    owner = await _seed_user(user_repository, "mgmt-owner2@example.com", UserRole.DOCTOR)
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=owner.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=doctor_b.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        f"/api/v1/patients/{patient.id}/assignments",
        headers=headers,
        json={"assignee_user_id": str(owner.id), "is_primary": True},
    )
    assert response.status_code == 409
