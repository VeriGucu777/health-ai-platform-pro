"""Patient list/get access via PatientAccessPolicy."""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.api.test_patients import PATIENT_PAYLOAD, _register_and_login


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Policy",
        last_name="Patient",
        date_of_birth=date(1991, 2, 2),
        gender="female",
    )


async def _login(client: AsyncClient, email: str, password: str = "securepass123") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_doctor(user_repository, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("securepass123"),
        first_name="Doc",
        last_name="Tor",
        role=UserRole.DOCTOR,
    )
    return await user_repository.create(user)


async def _seed_clinic_admin(user_repository, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("securepass123"),
        first_name="Admin",
        last_name="Clinic",
        role=UserRole.CLINIC_ADMIN,
    )
    return await user_repository.create(user)


@pytest.mark.asyncio
async def test_doctor_assigned_patient_get_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "assigned-owner@example.com")
    assignee = await _seed_doctor(user_repository, "assigned-doc@example.com")
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

    headers = await _login(client, "assigned-doc@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(patient.id)


@pytest.mark.asyncio
async def test_doctor_same_org_unassigned_get_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "unassigned-owner@example.com")
    other = await _seed_doctor(user_repository, "unassigned-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=other.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "unassigned-doc@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_doctor_cross_org_get_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    patient_org = uuid4()
    doctor_org = uuid4()
    owner = await _seed_doctor(user_repository, "cross-owner@example.com")
    doctor = await _seed_doctor(user_repository, "cross-doc@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=patient_org),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=doctor_org,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=doctor_org,
            patient_id=patient.id,
            assignee_user_id=doctor.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "cross-doc@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_doctor_legacy_owner_null_org_get_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    from app.core.security import hash_password

    owner = await user_repository.create(
        User(
            email="legacy-owner-get@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Legacy",
            last_name="Owner",
            role=UserRole.DOCTOR,
        ),
    )
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    headers = await _login(client, "legacy-owner-get@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clinic_admin_same_org_get_returns_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "admin-same-org@example.com")
    owner = await _seed_doctor(user_repository, "admin-patient-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "admin-same-org@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clinic_admin_cross_org_get_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    patient_org = uuid4()
    admin_org = uuid4()
    admin = await _seed_clinic_admin(user_repository, "admin-cross@example.com")
    owner = await _seed_doctor(user_repository, "admin-cross-owner@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=owner.id, organization_id=patient_org),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=admin_org,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "admin-cross@example.com")
    response = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_doctor_list_includes_assigned_and_legacy_owner_without_duplicates(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "list-doc@example.com")
    other_owner = await _seed_doctor(user_repository, "list-other-owner@example.com")

    legacy_owned = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=None),
    )
    org_owned_unassigned = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    org_owned = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=org_id),
    )
    assigned_only = await patient_repository.create(
        _patient(owner_id=other_owner.id, organization_id=org_id),
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
            patient_id=assigned_only.id,
            assignee_user_id=doctor.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=org_owned.id,
            assignee_user_id=doctor.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "list-doc@example.com")
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    ids = {item["id"] for item in data["items"]}
    assert str(org_owned_unassigned.id) not in ids
    assert ids == {str(legacy_owned.id), str(org_owned.id), str(assigned_only.id)}
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_clinic_admin_list_returns_org_patients(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    other_org = uuid4()
    admin = await _seed_clinic_admin(user_repository, "admin-list@example.com")
    owner = await _seed_doctor(user_repository, "admin-list-owner@example.com")
    in_org = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await patient_repository.create(_patient(owner_id=owner.id, organization_id=other_org))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )

    headers = await _login(client, "admin-list@example.com")
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(in_org.id)


@pytest.mark.asyncio
async def test_patient_role_still_denied_on_clinical_list(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "patient-role-list@example.com",
            "password": "securepass123",
            "first_name": "Pat",
            "last_name": "User",
            "role": "patient",
        },
    )
    headers = await _login(client, "patient-role-list@example.com")
    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403
