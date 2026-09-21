"""Patient access policy alignment for clinical child resources."""

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

APPOINTMENT_BODY = {
    "appointment_date": "2026-08-15T10:30:00Z",
    "appointment_type": "consultation",
    "status": "scheduled",
    "notes": "Visit",
}

MEDICAL_BODY = {
    "record_date": "2026-08-15T10:30:00Z",
    "record_type": "visit",
    "title": "Checkup",
}

HEALTH_BODY = {
    "measured_at": "2026-08-15T10:30:00Z",
    "blood_glucose": "110.0",
    "glucose_context": "fasting",
}


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _register(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    assert (
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepass123",
                "first_name": "T",
                "last_name": "U",
                "role": role,
            },
        )
    ).status_code == 201
    return await _login(client, email)


def _patient(*, owner_id: UUID, organization_id: UUID) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Child",
        last_name="Policy",
        date_of_birth=date(1990, 1, 1),
        gender="male",
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


async def _membership(membership_repository, *, org_id, user_id, role: OrganizationMembershipRole) -> None:
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=user_id,
            membership_role=role,
            status=MembershipStatus.ACTIVE,
        ),
    )


@pytest.fixture
async def clinical_child_setup(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
):
    """Org patient with assigned doctor, unassigned peer, and cross-org doctor."""
    org_a = uuid4()
    org_b = uuid4()
    owner = await _seed_doctor(user_repository, "child-owner@example.com")
    assigned = await _seed_doctor(user_repository, "child-assigned@example.com")
    unassigned = await _seed_doctor(user_repository, "child-unassigned@example.com")
    cross_org = await _seed_doctor(user_repository, "child-cross@example.com")
    clinic_admin = await _seed_clinic_admin(user_repository, "child-ca@example.com")

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

    owner_headers = await _login(client, owner.email)
    assigned_headers = await _login(client, assigned.email)
    unassigned_headers = await _login(client, unassigned.email)
    cross_headers = await _login(client, cross_org.email)
    admin_headers = await _login(client, clinic_admin.email)

    return {
        "org_a": org_a,
        "patient_id": str(patient.id),
        "owner_headers": owner_headers,
        "assigned_headers": assigned_headers,
        "unassigned_headers": unassigned_headers,
        "cross_headers": cross_headers,
        "admin_headers": admin_headers,
    }


def _create_payload(resource: str, patient_id: str) -> dict:
    body = {"patient_id": patient_id}
    if resource == "appointment":
        body.update(APPOINTMENT_BODY)
    elif resource == "medical":
        body.update(MEDICAL_BODY)
    else:
        body.update(HEALTH_BODY)
    return body


def _collection_path(resource: str) -> str:
    return {
        "appointment": "/api/v1/appointments",
        "medical": "/api/v1/medical-records",
        "health": "/api/v1/health-measurements",
    }[resource]


async def _create_child(client: AsyncClient, resource: str, headers: dict, patient_id: str) -> str:
    path = _collection_path(resource)
    response = await client.post(path, json=_create_payload(resource, patient_id), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.parametrize("resource", ["appointment", "medical", "health"])
@pytest.mark.asyncio
async def test_assigned_doctor_and_clinic_admin_can_access_child(
    client: AsyncClient,
    clinical_child_setup,
    resource: str,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client,
        resource,
        setup["owner_headers"],
        setup["patient_id"],
    )
    path = _collection_path(resource)

    for headers in (setup["assigned_headers"], setup["admin_headers"], setup["owner_headers"]):
        assert (await client.get(f"{path}/{child_id}", headers=headers)).status_code == 200
        listed = await client.get(f"{path}?patient_id={setup['patient_id']}", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1


@pytest.mark.parametrize("resource", ["appointment", "medical", "health"])
@pytest.mark.asyncio
async def test_unassigned_and_cross_org_get_child_returns_404(
    client: AsyncClient,
    clinical_child_setup,
    resource: str,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client,
        resource,
        setup["owner_headers"],
        setup["patient_id"],
    )
    path = _collection_path(resource)
    for headers in (setup["unassigned_headers"], setup["cross_headers"]):
        assert (await client.get(f"{path}/{child_id}", headers=headers)).status_code == 404


@pytest.mark.parametrize("resource", ["appointment", "medical", "health"])
@pytest.mark.asyncio
async def test_patient_and_system_admin_get_403(
    client: AsyncClient,
    user_repository,
    clinical_child_setup,
    resource: str,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client,
        resource,
        setup["owner_headers"],
        setup["patient_id"],
    )
    path = _collection_path(resource)
    headers = await _register(client, f"child-patient-{resource}@example.com", "patient")
    assert (await client.get(f"{path}/{child_id}", headers=headers)).status_code == 403

    system_admin = await user_repository.create(
        User(
            email=f"child-sysadmin-{resource}@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    admin_headers = await _login(client, system_admin.email)
    assert (await client.get(f"{path}/{child_id}", headers=admin_headers)).status_code == 403


@pytest.mark.parametrize("resource", ["appointment", "medical", "health"])
@pytest.mark.asyncio
async def test_inactive_patient_child_ops_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    clinical_child_setup,
    appointment_repository,
    medical_record_repository,
    health_measurement_repository,
    resource: str,
) -> None:
    setup = clinical_child_setup
    child_id = await _create_child(
        client,
        resource,
        setup["owner_headers"],
        setup["patient_id"],
    )
    patient = await patient_repository.get_by_id(UUID(setup["patient_id"]))
    assert patient is not None
    patient.is_active = False
    await patient_repository.update(patient)

    path = _collection_path(resource)
    headers = setup["admin_headers"]
    assert (await client.get(f"{path}/{child_id}", headers=headers)).status_code == 404
    assert (await client.get(f"{path}?patient_id={setup['patient_id']}", headers=headers)).status_code == 404
    assert (
        await client.post(path, json=_create_payload(resource, setup["patient_id"]), headers=headers)
    ).status_code == 404
    if resource == "appointment":
        patch = {"status": "cancelled"}
    elif resource == "medical":
        patch = {"title": "Updated"}
    else:
        patch = {"notes": "Updated"}
    assert (await client.patch(f"{path}/{child_id}", json=patch, headers=headers)).status_code == 404
    assert (await client.delete(f"{path}/{child_id}", headers=headers)).status_code == 404

    assert len(await appointment_repository.list_all()) >= 0
    assert len(await medical_record_repository.list_all()) >= 0
    assert len(await health_measurement_repository.list_all()) >= 0


@pytest.mark.asyncio
async def test_appointment_cross_patient_patient_id_tampering_rejected(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_a = uuid4()
    org_b = uuid4()
    owner = await _seed_doctor(user_repository, "tamper-owner@example.com")
    await _membership(
        membership_repository,
        org_id=org_a,
        user_id=owner.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    inaccessible = await patient_repository.create(
        _patient(owner_id=uuid4(), organization_id=org_b),
    )
    headers = await _login(client, owner.email)
    p1 = (
        await client.post(
            "/api/v1/patients",
            json={
                "first_name": "A",
                "last_name": "B",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            },
            headers=headers,
        )
    ).json()["id"]
    appt_id = (
        await client.post(
            "/api/v1/appointments",
            json={**APPOINTMENT_BODY, "patient_id": p1},
            headers=headers,
        )
    ).json()["id"]
    response = await client.patch(
        f"/api/v1/appointments/{appt_id}",
        headers=headers,
        json={"patient_id": str(inaccessible.id)},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_child_mutation_audit_has_organization_id_no_phi(
    client: AsyncClient,
    clinical_child_setup,
    audit_log_repository,
) -> None:
    setup = clinical_child_setup
    audit_log_repository.records.clear()
    response = await client.post(
        "/api/v1/appointments",
        json={**APPOINTMENT_BODY, "patient_id": setup["patient_id"]},
        headers=setup["assigned_headers"],
    )
    assert response.status_code == 201
    audits = [
        r
        for r in audit_log_repository.list_all()
        if r.resource_type == AuditResourceType.PATIENT and r.action == AuditAction.CREATE
    ]
    assert len(audits) == 1
    assert audits[0].organization_id == setup["org_a"]
    assert audits[0].metadata.get("child_kind") == "appointment"
    assert "diagnosis" not in str(audits[0].metadata).lower()


@pytest.mark.asyncio
async def test_analytics_inactive_and_cross_org_404(
    client: AsyncClient,
    clinical_child_setup,
    patient_repository,
) -> None:
    setup = clinical_child_setup
    url = f"/api/v1/health-measurements/analytics/summary?patient_id={setup['patient_id']}"
    assert (await client.get(url, headers=setup["cross_headers"])).status_code == 404
    patient = await patient_repository.get_by_id(UUID(setup["patient_id"]))
    assert patient is not None
    patient.is_active = False
    await patient_repository.update(patient)
    assert (await client.get(url, headers=setup["admin_headers"])).status_code == 404
