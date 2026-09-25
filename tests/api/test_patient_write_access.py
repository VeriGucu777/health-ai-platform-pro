"""Organization-aware patient create/update/delete write access."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.api.test_patients import PATIENT_PAYLOAD, _register_and_login


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


def _patient(*, owner_id: UUID, organization_id: UUID | None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Write",
        last_name="Target",
        date_of_birth=date(1992, 3, 3),
        gender="female",
    )


@pytest.mark.asyncio
async def test_clinic_admin_create_sets_organization_id(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
    audit_log_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "write-ca-create@example.com")
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, "write-ca-create@example.com")
    audit_log_repository.records.clear()

    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    patient_id = UUID(response.json()["id"])
    stored = await patient_repository.get_by_id(patient_id)
    assert stored is not None
    assert stored.organization_id == org_id
    assert stored.owner_id == admin.id

    audits = [
        r
        for r in audit_log_repository.list_all()
        if r.resource_type == AuditResourceType.PATIENT and r.action == AuditAction.CREATE
    ]
    assert len(audits) == 1
    assert audits[0].organization_id == org_id


@pytest.mark.asyncio
async def test_doctor_self_register_cannot_create_org_patient(
    client: AsyncClient,
) -> None:
    """Pilot policy: patient create is clinic_admin-only even for registered doctors."""
    headers = await _register_and_login(client, email="write-doc-create@example.com")
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_doctor_without_membership_create_forbidden(
    client: AsyncClient,
    user_repository,
) -> None:
    await _seed_doctor(user_repository, "write-doc-nomember@example.com")
    headers = await _login(client, "write-doc-nomember@example.com")
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_clinic_admin_same_org_update_success(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    admin = await _seed_clinic_admin(user_repository, "write-ca-upd@example.com")
    owner = await _seed_doctor(user_repository, "write-ca-patient-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, "write-ca-upd@example.com")
    response = await client.patch(
        f"/api/v1/patients/{patient.id}",
        json={"first_name": "UpdatedByAdmin"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "UpdatedByAdmin"


@pytest.mark.asyncio
async def test_doctor_assigned_same_org_update_success(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "write-upd-owner@example.com")
    doctor = await _seed_doctor(user_repository, "write-upd-assigned@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    for user_id in (owner.id, doctor.id):
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
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
    headers = await _login(client, "write-upd-assigned@example.com")
    response = await client.patch(
        f"/api/v1/patients/{patient.id}",
        json={"notes": "Assigned update"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_doctor_unassigned_update_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "write-unassigned-owner@example.com")
    other = await _seed_doctor(user_repository, "write-unassigned-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    for user_id in (owner.id, other.id):
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )
    headers = await _login(client, "write-unassigned-doc@example.com")
    response = await client.patch(
        f"/api/v1/patients/{patient.id}",
        json={"first_name": "Nope"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cross_org_update_returns_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_a, org_b = uuid4(), uuid4()
    owner = await _seed_doctor(user_repository, "write-cross-owner@example.com")
    outsider = await _seed_doctor(user_repository, "write-cross-outsider@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_a))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_a,
            user_id=owner.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_b,
            user_id=outsider.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, "write-cross-outsider@example.com")
    response = await client.patch(
        f"/api/v1/patients/{patient.id}",
        json={"first_name": "Cross"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_same_rules_as_update(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "write-del-owner@example.com")
    unassigned = await _seed_doctor(user_repository, "write-del-unassigned@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    for user_id in (owner.id, unassigned.id):
        await membership_repository.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=user_id,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )
    owner_headers = await _login(client, "write-del-owner@example.com")
    unassigned_headers = await _login(client, "write-del-unassigned@example.com")

    deny = await client.delete(f"/api/v1/patients/{patient.id}", headers=unassigned_headers)
    assert deny.status_code == 404

    ok = await client.delete(f"/api/v1/patients/{patient.id}", headers=owner_headers)
    assert ok.status_code == 204
    stored = await patient_repository.get_by_id(patient.id)
    assert stored is not None and stored.is_active is False


@pytest.mark.asyncio
async def test_patient_role_write_forbidden(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    await user_repository.create(
        User(
            email="write-patient-role@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Pat",
            last_name="Ient",
            role=UserRole.PATIENT,
        ),
    )
    doctor = await _seed_doctor(user_repository, "write-patient-target-doc@example.com")
    patient = await patient_repository.create(
        _patient(owner_id=doctor.id, organization_id=uuid4()),
    )
    headers = await _login(client, "write-patient-role@example.com")
    for method, url, kwargs in (
        ("post", "/api/v1/patients", {"json": PATIENT_PAYLOAD}),
        ("patch", f"/api/v1/patients/{patient.id}", {"json": {"first_name": "X"}}),
        ("delete", f"/api/v1/patients/{patient.id}", {}),
    ):
        response = await getattr(client, method)(url, headers=headers, **kwargs)
        assert response.status_code == 403, method
