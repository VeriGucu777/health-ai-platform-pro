"""Clinic admin patient onboarding + consent (acceptance-style API tests)."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.support.patient_test_constants import PATIENT_PAYLOAD


async def _login(client: AsyncClient, email: str, password: str = "securepass123") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
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


@pytest.mark.asyncio
async def test_clinic_admin_onboarding_happy_path_create_list_and_consent(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-happy@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)

    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert create.status_code == 201
    patient_id = UUID(create.json()["id"])
    stored = await patient_repository.get_by_id(patient_id)
    assert stored is not None
    assert stored.organization_id == org_id
    assert stored.owner_id == admin.id

    listing = await client.get("/api/v1/patients", headers=headers)
    assert listing.status_code == 200
    listed_ids = {row["id"] for row in listing.json()["items"]}
    assert str(patient_id) in listed_ids

    grant = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert grant.status_code == 201
    assert grant.json()["status"] == "granted"
    assert grant.json()["granted_at"] is not None


@pytest.mark.asyncio
async def test_clinic_admin_create_rejects_extra_organization_id(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-no-org-inject@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    payload = {**PATIENT_PAYLOAD, "organization_id": str(uuid4())}
    response = await client.post("/api/v1/patients", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_clinic_admin_create_invalid_input_returns_422(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-invalid@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post(
        "/api/v1/patients",
        json={"first_name": "", "last_name": "X", "date_of_birth": "1990-01-01", "gender": "female"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_clinic_admin_duplicate_active_consent_returns_409(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-dup-consent@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_doctor_cannot_create_patient_via_api(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    doctor = await _seed_doctor(user_repository, "onboard-doc-create-block@example.com")
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
async def test_doctor_cannot_grant_consent_for_org_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-admin-consent@example.com")
    doctor = await _seed_doctor(user_repository, "onboard-doc-consent@example.com")
    for user_id, role in [
        (admin.id, OrganizationMembershipRole.CLINIC_ADMIN),
        (doctor.id, OrganizationMembershipRole.DOCTOR),
    ]:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=role,
                status=MembershipStatus.ACTIVE,
            ),
        )
    admin_headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=admin_headers)
    patient_id = create.json()["id"]

    doctor_headers = await _login(client, doctor.email)
    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=doctor_headers,
        json={"consent_type": "clinical_data_processing"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_doctor_does_not_see_unassigned_admin_created_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-unassigned@example.com")
    doctor = await _seed_doctor(user_repository, "onboard-doc-list@example.com")
    for user_id, role in [
        (admin.id, OrganizationMembershipRole.CLINIC_ADMIN),
        (doctor.id, OrganizationMembershipRole.DOCTOR),
    ]:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=role,
                status=MembershipStatus.ACTIVE,
            ),
        )
    admin_headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=admin_headers)
    patient_id = create.json()["id"]

    doctor_headers = await _login(client, doctor.email)
    listing = await client.get("/api/v1/patients", headers=doctor_headers)
    assert listing.status_code == 200
    doctor_ids = {row["id"] for row in listing.json()["items"]}
    assert patient_id not in doctor_ids

    get_one = await client.get(f"/api/v1/patients/{patient_id}", headers=doctor_headers)
    assert get_one.status_code == 404


@pytest.mark.asyncio
async def test_doctor_sees_patient_after_assignment(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-assigned@example.com")
    doctor = await _seed_doctor(user_repository, "onboard-doc-assigned@example.com")
    for user_id, role in [
        (admin.id, OrganizationMembershipRole.CLINIC_ADMIN),
        (doctor.id, OrganizationMembershipRole.DOCTOR),
    ]:
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=role,
                status=MembershipStatus.ACTIVE,
            ),
        )
    admin_headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=admin_headers)
    patient_id = UUID(create.json()["id"])

    assign = await client.post(
        f"/api/v1/patients/{patient_id}/assignments",
        headers=admin_headers,
        json={"assignee_user_id": str(doctor.id), "is_primary": True},
    )
    assert assign.status_code == 201

    doctor_headers = await _login(client, doctor.email)
    listing = await client.get("/api/v1/patients", headers=doctor_headers)
    assert str(patient_id) in {row["id"] for row in listing.json()["items"]}


@pytest.mark.asyncio
async def test_cross_org_admin_create_consent_masked_as_404(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_a = uuid4()
    org_b = uuid4()
    admin_a = await _seed_clinic_admin(user_repository, "onboard-org-a@example.com")
    admin_b = await _seed_clinic_admin(user_repository, "onboard-org-b@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_a,
            user_id=admin_a.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_b,
            user_id=admin_b.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    patient_b = await patient_repository.create(
        Patient(
            owner_id=admin_b.id,
            organization_id=org_b,
            first_name="Other",
            last_name="Org",
            date_of_birth=date(1991, 2, 2),
            gender="male",
        ),
    )
    headers_a = await _login(client, admin_a.email)
    response = await client.post(
        f"/api/v1/patients/{patient_b.id}/consents",
        headers=headers_a,
        json={"consent_type": "clinical_data_processing"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_inactive_clinic_admin_membership_cannot_create(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-inactive@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.INACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_patient_create_and_consent_return_401(
    client: AsyncClient,
    patient_repository,
) -> None:
    patient = await patient_repository.create(
        Patient(
            owner_id=uuid4(),
            organization_id=uuid4(),
            first_name="Open",
            last_name="Patient",
            date_of_birth=date(1985, 1, 1),
            gender="female",
        ),
    )
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD)
    assert create.status_code == 401
    consent = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        json={"consent_type": "clinical_data_processing"},
    )
    assert consent.status_code == 401


@pytest.mark.asyncio
async def test_malformed_consent_request_returns_422(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-malformed@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = create.json()["id"]
    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"consent_type": "not_a_valid_type"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_consent_revoke_and_update_preserves_history(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "onboard-consent-update@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    create = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = create.json()["id"]

    grant = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={"consent_type": "clinical_data_processing"},
    )
    consent_id = grant.json()["id"]
    revoke = await client.patch(
        f"/api/v1/patients/{patient_id}/consents/{consent_id}",
        headers=headers,
    )
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    history = await client.get(f"/api/v1/patients/{patient_id}/consents", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["items"]) >= 1
