"""Clinical timeline, risk, and PDF access via PatientAccessPolicy."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole

ASSESSMENT_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"
REPORT_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Clinical",
        last_name="Read",
        date_of_birth=date(1990, 3, 3),
        gender="male",
    )


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


async def _seed_org_patient_with_assignment(
    *,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
    owner_email: str,
    assignee_email: str,
) -> tuple[User, User, Patient]:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, owner_email)
    assignee = await _seed_doctor(user_repository, assignee_email)
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=assignee.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=assignee.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    return owner, assignee, patient


@pytest.mark.asyncio
async def test_assigned_doctor_clinical_timeline_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    _, assignee, patient = await _seed_org_patient_with_assignment(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
        owner_email="tl-owner@example.com",
        assignee_email="tl-assignee@example.com",
    )
    headers = await _login(client, assignee.email)
    response = await client.get(
        f"/api/v1/patients/{patient.id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["patient_id"] == str(patient.id)


@pytest.mark.asyncio
async def test_assigned_doctor_risk_assessments_return_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    _, assignee, patient = await _seed_org_patient_with_assignment(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
        owner_email="risk-owner@example.com",
        assignee_email="risk-assignee@example.com",
    )
    headers = await _login(client, assignee.email)
    pid = str(patient.id)
    for path in (
        f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{pid}/risk-assessments/heart-disease?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{pid}/risk-assessments/stroke?{ASSESSMENT_DATE_RANGE}",
    ):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200, path
        assert response.json()["patient_id"] == pid


@pytest.mark.asyncio
async def test_assigned_doctor_pdf_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    _, assignee, patient = await _seed_org_patient_with_assignment(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
        owner_email="pdf-owner@example.com",
        assignee_email="pdf-assignee@example.com",
    )
    headers = await _login(client, assignee.email)
    response = await client.get(
        f"/api/v1/patients/{patient.id}/reports/health-summary.pdf?{REPORT_DATE_RANGE}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_clinic_admin_same_org_clinical_reads_return_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "admin-read-owner@example.com")
    admin = await _seed_clinic_admin(user_repository, "admin-read-admin@example.com")
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
    pid = str(patient.id)
    paths = [
        f"/api/v1/patients/{pid}/clinical-timeline",
        f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{pid}/reports/health-summary.pdf?{REPORT_DATE_RANGE}",
    ]
    for path in paths:
        response = await client.get(path, headers=headers)
        assert response.status_code == 200, path


@pytest.mark.asyncio
async def test_unassigned_doctor_clinical_reads_return_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "unassigned-cr-owner@example.com")
    other = await _seed_doctor(user_repository, "unassigned-cr-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=other.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, other.email)
    pid = str(patient.id)
    paths = [
        f"/api/v1/patients/{pid}/clinical-timeline",
        f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{pid}/reports/health-summary.pdf?{REPORT_DATE_RANGE}",
    ]
    for path in paths:
        assert (await client.get(path, headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_cross_org_clinical_reads_return_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_a, org_b = uuid4(), uuid4()
    owner = await _seed_doctor(user_repository, "cross-cr-owner@example.com")
    outsider = await _seed_doctor(user_repository, "cross-cr-outsider@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_a))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_b,
            user_id=outsider.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, outsider.email)
    pid = str(patient.id)
    assert (
        await client.get(f"/api/v1/patients/{pid}/clinical-timeline", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_legacy_owner_clinical_reads_return_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    owner = await _seed_doctor(user_repository, "legacy-cr-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    headers = await _login(client, owner.email)
    pid = str(patient.id)
    assert (
        await client.get(f"/api/v1/patients/{pid}/clinical-timeline", headers=headers)
    ).status_code == 200
    assert (
        await client.get(
            f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
            headers=headers,
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_legacy_non_owner_clinical_reads_return_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    owner = await _seed_doctor(user_repository, "legacy-no-owner@example.com")
    other = await _seed_doctor(user_repository, "legacy-no-other@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    headers = await _login(client, other.email)
    pid = str(patient.id)
    assert (
        await client.get(f"/api/v1/patients/{pid}/clinical-timeline", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_patient_role_clinical_reads_return_403(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "clinical-patient@example.com",
            "password": "securepass123",
            "first_name": "Pat",
            "last_name": "Ient",
            "role": "patient",
        },
    )
    headers = await _login(client, "clinical-patient@example.com")
    pid = "00000000-0000-4000-8000-000000000099"
    assert (
        await client.get(f"/api/v1/patients/{pid}/clinical-timeline", headers=headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_clinical_read_audit_success_persisted(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
    audit_log_repository,
) -> None:
    _, assignee, patient = await _seed_org_patient_with_assignment(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
        owner_email="audit-cr-owner@example.com",
        assignee_email="audit-cr-assignee@example.com",
    )
    headers = await _login(client, assignee.email)
    response = await client.get(
        f"/api/v1/patients/{patient.id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200

    records = audit_log_repository.list_all()
    matches = [
        r
        for r in records
        if r.resource_type == AuditResourceType.PATIENT_CLINICAL_TIMELINE
        and r.action == AuditAction.VIEW
        and r.outcome == AuditOutcome.SUCCESS
        and r.resource_id == patient.id
    ]
    assert len(matches) >= 1
