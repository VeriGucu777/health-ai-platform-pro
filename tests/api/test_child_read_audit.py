"""PHI-safe READ audit for clinical child resources."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.domain.patient.errors import PatientHardDeleteForbiddenError
from tests.api.test_child_resource_policy import (
    _create_child,
    _login,
    _seed_clinic_admin,
    _seed_doctor,
)

ANALYTICS_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


@pytest.fixture
async def clinical_child_setup(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
):
    """Org patient with assigned doctor, unassigned peer, and cross-org doctor."""
    from tests.api.test_child_resource_policy import _membership, _patient

    org_a = uuid4()
    org_b = uuid4()
    owner = await _seed_doctor(user_repository, "read-audit-owner@example.com")
    assigned = await _seed_doctor(user_repository, "read-audit-assigned@example.com")
    unassigned = await _seed_doctor(user_repository, "read-audit-unassigned@example.com")
    cross_org = await _seed_doctor(user_repository, "read-audit-cross@example.com")
    clinic_admin = await _seed_clinic_admin(user_repository, "read-audit-ca@example.com")

    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_a))
    for uid in (owner.id, assigned.id, unassigned.id):
        await _membership(
            membership_repository,
            org_id=org_a,
            user_id=uid,
            role=OrganizationMembershipRole.DOCTOR,
        )
    await _membership(
        membership_repository,
        org_id=org_b,
        user_id=cross_org.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    await _membership(
        membership_repository,
        org_id=org_a,
        user_id=clinic_admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_a,
            patient_id=patient.id,
            assignee_user_id=assigned.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )

    return {
        "org_a": org_a,
        "patient_id": str(patient.id),
        "owner_headers": await _login(client, owner.email),
        "assigned_headers": await _login(client, assigned.email),
        "unassigned_headers": await _login(client, unassigned.email),
        "cross_headers": await _login(client, cross_org.email),
        "admin_headers": await _login(client, clinic_admin.email),
    }


def _patient(*, owner_id: UUID, organization_id: UUID) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Audit",
        last_name="Read",
        date_of_birth=date(1990, 1, 1),
        gender="male",
    )


def _child_audits(audit_log_repository, *, action: AuditAction):
    return [
        r
        for r in audit_log_repository.list_all()
        if r.resource_type == AuditResourceType.PATIENT and r.action == action
    ]


@pytest.mark.asyncio
async def test_assigned_doctor_child_list_and_view_audit_success(
    client: AsyncClient,
    clinical_child_setup,
    audit_log_repository,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client, "appointment", setup["owner_headers"], setup["patient_id"]
    )
    audit_log_repository.records.clear()
    headers = setup["assigned_headers"]
    pid = setup["patient_id"]

    list_resp = await client.get(
        f"/api/v1/appointments?patient_id={pid}&page=1&page_size=20",
        headers=headers,
    )
    assert list_resp.status_code == 200
    view_resp = await client.get(f"/api/v1/appointments/{child_id}", headers=headers)
    assert view_resp.status_code == 200

    list_audits = _child_audits(audit_log_repository, action=AuditAction.LIST)
    view_audits = _child_audits(audit_log_repository, action=AuditAction.VIEW)
    assert len(list_audits) == 1
    assert len(view_audits) == 1
    assert list_audits[0].outcome == AuditOutcome.SUCCESS
    assert view_audits[0].outcome == AuditOutcome.SUCCESS
    assert list_audits[0].organization_id == setup["org_a"]
    assert view_audits[0].organization_id == setup["org_a"]
    assert list_audits[0].resource_id == UUID(pid)
    assert view_audits[0].resource_id == UUID(pid)
    assert view_audits[0].metadata.get("child_id") == child_id
    assert "diagnosis" not in str(list_audits[0].metadata).lower()


@pytest.mark.asyncio
async def test_clinic_admin_child_read_audit_success(
    client: AsyncClient,
    clinical_child_setup,
    audit_log_repository,
) -> None:
    setup = clinical_child_setup
    await _create_child(client, "medical", setup["owner_headers"], setup["patient_id"])
    audit_log_repository.records.clear()
    headers = setup["admin_headers"]
    pid = setup["patient_id"]
    response = await client.get(f"/api/v1/medical-records?patient_id={pid}", headers=headers)
    assert response.status_code == 200
    audits = _child_audits(audit_log_repository, action=AuditAction.LIST)
    assert len(audits) == 1
    assert audits[0].organization_id == setup["org_a"]


@pytest.mark.asyncio
async def test_unassigned_cross_org_inactive_read_audit_failure_no_patient_leak(
    client: AsyncClient,
    clinical_child_setup,
    patient_repository,
    audit_log_repository,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client, "health", setup["owner_headers"], setup["patient_id"]
    )
    pid = setup["patient_id"]
    path_list = f"/api/v1/health-measurements?patient_id={pid}"
    path_view = f"/api/v1/health-measurements/{child_id}"
    analytics = f"/api/v1/health-measurements/analytics/summary?patient_id={pid}&{ANALYTICS_RANGE}"

    for headers in (setup["unassigned_headers"], setup["cross_headers"]):
        audit_log_repository.records.clear()
        assert (await client.get(path_list, headers=headers)).status_code == 404
        assert (await client.get(path_view, headers=headers)).status_code == 404
        assert (await client.get(analytics, headers=headers)).status_code == 404
        for row in audit_log_repository.list_all():
            if row.action == AuditAction.VIEW and row.outcome == AuditOutcome.FAILURE:
                assert row.resource_id is None

    patient = await patient_repository.get_by_id(UUID(pid))
    assert patient is not None
    patient.is_active = False
    await patient_repository.update(patient)
    audit_log_repository.records.clear()
    headers = setup["admin_headers"]
    assert (await client.get(path_list, headers=headers)).status_code == 404
    failures = [
        r
        for r in audit_log_repository.list_all()
        if r.outcome == AuditOutcome.FAILURE and r.action in (AuditAction.LIST, AuditAction.VIEW)
    ]
    assert failures
    assert all(r.resource_id is None for r in failures)


@pytest.mark.asyncio
async def test_analytics_views_audit_success_once_each(
    client: AsyncClient,
    clinical_child_setup,
    audit_log_repository,
) -> None:
    setup = clinical_child_setup
    headers = setup["assigned_headers"]
    pid = setup["patient_id"]
    audit_log_repository.records.clear()

    assert (
        await client.get(
            f"/api/v1/health-measurements/analytics/summary?patient_id={pid}&{ANALYTICS_RANGE}",
            headers=headers,
        )
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/health-measurements/analytics/trends?patient_id={pid}&period=weekly&{ANALYTICS_RANGE}",
            headers=headers,
        )
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/health-measurements/analytics/insights?patient_id={pid}&{ANALYTICS_RANGE}",
            headers=headers,
        )
    ).status_code == 200

    view_audits = _child_audits(audit_log_repository, action=AuditAction.VIEW)
    assert len(view_audits) == 3
    endpoints = {row.metadata.get("analytics_endpoint") for row in view_audits}
    assert endpoints == {"summary", "trends", "insights"}
    assert all(row.organization_id == setup["org_a"] for row in view_audits)


@pytest.mark.asyncio
async def test_public_patient_delete_soft_delete_and_hard_delete_forbidden(
    client: AsyncClient,
    patient_repository,
) -> None:
    email = "soft-read-audit-del@example.com"
    assert (
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepass123",
                "first_name": "Del",
                "last_name": "Test",
                "role": "doctor",
            },
        )
    ).status_code == 201
    headers = await _login(client, email)
    created = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "Keep",
            "last_name": "Row",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        },
        headers=headers,
    )
    patient_id = UUID(created.json()["id"])
    assert (await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)).status_code == 204
    stored = await patient_repository.get_by_id(patient_id)
    assert stored is not None and stored.is_active is False

    with pytest.raises(PatientHardDeleteForbiddenError):
        await patient_repository.delete(patient_id)
