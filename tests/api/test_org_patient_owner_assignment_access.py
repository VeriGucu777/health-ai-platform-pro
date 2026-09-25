"""Org-scoped patients require assignment; owner_id alone is not sufficient."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole

ASSESSMENT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"
REPORT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Org",
        last_name="Scope",
        date_of_birth=date(1991, 1, 1),
        gender="female",
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


@pytest.mark.asyncio
async def test_org_patient_owner_without_assignment_get_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "org-owner-no-assign@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_org_patient_owner_with_assignment_get_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "org-owner-with-assign@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=doctor.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_org_patient_owner_without_assignment_excluded_from_list(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "org-owner-list@example.com")
    unassigned_owned = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    assigned = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    legacy = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=None),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=assigned.id,
            assignee_user_id=doctor.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["items"]}
    assert str(unassigned_owned.id) not in ids
    assert str(assigned.id) in ids
    assert str(legacy.id) in ids


@pytest.mark.asyncio
async def test_org_patient_owner_without_assignment_clinical_reads_return_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "org-owner-clinical@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    pid = str(patient.id)
    paths = [
        f"/api/v1/patients/{pid}/clinical-timeline",
        f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_RANGE}",
        f"/api/v1/patients/{pid}/reports/health-summary.pdf?{REPORT_RANGE}",
    ]
    for path in paths:
        response = await client.get(path, headers=headers)
        assert response.status_code == 404, path
