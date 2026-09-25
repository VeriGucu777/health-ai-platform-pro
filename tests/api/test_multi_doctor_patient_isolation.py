"""Multi-doctor organization patient isolation (acceptance-style API tests)."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.api.test_patients import PATIENT_PAYLOAD

ASSESSMENT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"
REPORT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"


def _patient(*, owner_id, organization_id, label: str) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name=label,
        last_name="Isolation",
        date_of_birth=date(1993, 5, 5),
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


async def _seed_multi_doctor_org(
    *,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
):
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "multi-admin@example.com")
    doctor_a = await _seed_doctor(user_repository, "multi-doctor-a@example.com")
    doctor_b = await _seed_doctor(user_repository, "multi-doctor-b@example.com")
    owner = await _seed_doctor(user_repository, "multi-patient-owner@example.com")

    for user_id, role in [
        (admin.id, OrganizationMembershipRole.CLINIC_ADMIN),
        (doctor_a.id, OrganizationMembershipRole.DOCTOR),
        (doctor_b.id, OrganizationMembershipRole.DOCTOR),
        (owner.id, OrganizationMembershipRole.DOCTOR),
    ]:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=role,
                status=MembershipStatus.ACTIVE,
            ),
        )

    patient_a1 = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=org_id, label="A1"),
    )
    patient_a2 = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=org_id, label="A2"),
    )
    patient_b1 = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=org_id, label="B1"),
    )
    patient_b2 = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=org_id, label="B2"),
    )

    for patient_id in (patient_a1.id, patient_a2.id):
        await assignment_repository.create(
            PatientAssignment(
                organization_id=org_id,
                patient_id=patient_id,
                assignee_user_id=doctor_a.id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
            ),
        )
    for patient_id in (patient_b1.id, patient_b2.id):
        await assignment_repository.create(
            PatientAssignment(
                organization_id=org_id,
                patient_id=patient_id,
                assignee_user_id=doctor_b.id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
            ),
        )

    return {
        "org_id": org_id,
        "admin": admin,
        "doctor_a": doctor_a,
        "doctor_b": doctor_b,
        "patient_a1": patient_a1,
        "patient_a2": patient_a2,
        "patient_b1": patient_b1,
        "patient_b2": patient_b2,
    }


@pytest.mark.asyncio
async def test_doctor_a_sees_only_assigned_patients_in_list(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["doctor_a"].email)
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["items"]}
    assert ids == {str(setup["patient_a1"].id), str(setup["patient_a2"].id)}


@pytest.mark.asyncio
async def test_doctor_a_cannot_see_doctor_b_patients_in_list(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["doctor_a"].email)
    response = await client.get("/api/v1/patients", headers=headers)
    ids = {row["id"] for row in response.json()["items"]}
    assert str(setup["patient_b1"].id) not in ids
    assert str(setup["patient_b2"].id) not in ids


@pytest.mark.asyncio
async def test_doctor_a_direct_get_doctor_b_patient_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["doctor_a"].email)
    response = await client.get(
        f"/api/v1/patients/{setup['patient_b1'].id}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_doctor_b_symmetric_isolation_from_doctor_a_patients(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["doctor_b"].email)
    listing = await client.get("/api/v1/patients", headers=headers)
    ids = {row["id"] for row in listing.json()["items"]}
    assert ids == {str(setup["patient_b1"].id), str(setup["patient_b2"].id)}
    denied = await client.get(
        f"/api/v1/patients/{setup['patient_a1'].id}",
        headers=headers,
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_doctor_a_blocked_on_doctor_b_patient_clinical_endpoints(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["doctor_a"].email)
    pid = str(setup["patient_b1"].id)
    paths = [
        f"/api/v1/patients/{pid}/clinical-timeline",
        f"/api/v1/patients/{pid}/risk-assessments/diabetes?{ASSESSMENT_RANGE}",
        f"/api/v1/patients/{pid}/reports/health-summary.pdf?{REPORT_RANGE}",
    ]
    for path in paths:
        response = await client.get(path, headers=headers)
        assert response.status_code == 404, path


@pytest.mark.asyncio
async def test_clinic_admin_lists_all_org_patients(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    headers = await _login(client, setup["admin"].email)
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["items"]}
    assert ids == {
        str(setup["patient_a1"].id),
        str(setup["patient_a2"].id),
        str(setup["patient_b1"].id),
        str(setup["patient_b2"].id),
    }


@pytest.mark.asyncio
async def test_clinic_admin_create_patient_in_org(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "multi-admin-create@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_doctor_in_org_cannot_create_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "multi-doc-create-deny@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, doctor.email)
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_deactivating_assignment_revokes_doctor_list_and_detail_access(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    assignment = await assignment_repository.get_by_patient_and_assignee(
        setup["patient_a1"].id,
        setup["doctor_a"].id,
    )
    assert assignment is not None

    admin_headers = await _login(client, setup["admin"].email)
    deactivate = await client.patch(
        f"/api/v1/patients/{setup['patient_a1'].id}/assignments/{assignment.id}",
        headers=admin_headers,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["status"] == "inactive"

    doctor_headers = await _login(client, setup["doctor_a"].email)
    listing = await client.get("/api/v1/patients", headers=doctor_headers)
    listed_ids = {row["id"] for row in listing.json()["items"]}
    assert str(setup["patient_a1"].id) not in listed_ids
    assert str(setup["patient_a2"].id) in listed_ids

    detail = await client.get(
        f"/api/v1/patients/{setup['patient_a1'].id}",
        headers=doctor_headers,
    )
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_inactive_doctor_membership_cannot_list_org_patients(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    membership = await membership_repository.get_by_organization_and_user(
        setup["org_id"],
        setup["doctor_a"].id,
    )
    assert membership is not None
    membership.status = MembershipStatus.INACTIVE
    await membership_repository.update(membership)

    headers = await _login(client, setup["doctor_a"].email)
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_inactive_assignment_blocks_doctor_detail_access(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    setup = await _seed_multi_doctor_org(
        user_repository=user_repository,
        patient_repository=patient_repository,
        membership_repository=membership_repository,
        assignment_repository=assignment_repository,
    )
    assignment = await assignment_repository.get_by_patient_and_assignee(
        setup["patient_a2"].id,
        setup["doctor_a"].id,
    )
    assert assignment is not None
    assignment.status = AssignmentStatus.INACTIVE
    await assignment_repository.update(assignment)

    headers = await _login(client, setup["doctor_a"].email)
    response = await client.get(
        f"/api/v1/patients/{setup['patient_a2'].id}",
        headers=headers,
    )
    assert response.status_code == 404
