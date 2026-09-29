"""RBAC-aligned org patient setup for API integration tests (Task 1 policy)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from tests.support.patient_test_constants import PATIENT_PAYLOAD

__all__ = [
    "PATIENT_PAYLOAD",
    "create_assigned_patient_for_doctor_email",
    "create_assigned_patients_for_doctor_email",
    "create_assigned_patient_for_doctor_headers",
    "doctor_email_from_headers",
    "register_and_login_doctor",
    "register_clinic_admin_and_login",
    "seed_clinic_admin_membership",
]


async def _login(client: AsyncClient, email: str, *, password: str = "securepass123") -> dict[str, str]:
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


async def _membership(
    membership_repository,
    *,
    org_id: UUID,
    user_id: UUID,
    role: OrganizationMembershipRole,
) -> None:
    from app.domain.organization.entities import OrganizationMembership

    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=user_id,
            membership_role=role,
            status=MembershipStatus.ACTIVE,
        ),
    )


async def register_and_login_doctor(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict[str, str]:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": "doctor",
        },
    )
    assert register_response.status_code == 201
    return await _login(client, email, password=password)


async def register_clinic_admin_and_login(
    client: AsyncClient,
    user_repository,
    membership_repository,
    *,
    email: str,
    organization_id: UUID | None = None,
) -> tuple[dict[str, str], UUID, User]:
    """Register clinic admin via API is not public; seed user + membership and login."""
    org_id = organization_id or uuid4()
    admin = await _seed_clinic_admin(user_repository, email)
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    return await _login(client, admin.email), org_id, admin


async def seed_clinic_admin_membership(
    user_repository,
    membership_repository,
    *,
    admin_email: str,
    organization_id: UUID,
) -> User:
    admin = await _seed_clinic_admin(user_repository, admin_email)
    await _membership(
        membership_repository,
        org_id=organization_id,
        user_id=admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    return admin


async def doctor_email_from_headers(client: AsyncClient, doctor_headers: dict[str, str]) -> str:
    me = await client.get("/api/v1/auth/me", headers=doctor_headers)
    assert me.status_code == 200
    return me.json()["email"]


async def create_assigned_patient_for_doctor_email(
    client: AsyncClient,
    user_repository,
    membership_repository,
    *,
    doctor_email: str,
    patient_payload: dict[str, Any] | None = None,
    extra_org_doctor_emails: tuple[str, ...] = (),
    admin_email: str | None = None,
) -> str:
    """Clinic admin creates org patient; doctor receives ACTIVE assignment."""
    doctor = await user_repository.get_by_email(doctor_email)
    assert doctor is not None
    org_id = uuid4()
    admin = await _seed_clinic_admin(
        user_repository,
        admin_email or f"harness-ca-{doctor_email}",
    )
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=doctor.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    for peer_email in extra_org_doctor_emails:
        peer = await user_repository.get_by_email(peer_email)
        assert peer is not None
        await _membership(
            membership_repository,
            org_id=org_id,
            user_id=peer.id,
            role=OrganizationMembershipRole.DOCTOR,
        )
    admin_headers = await _login(client, admin.email)
    payload = dict(patient_payload or PATIENT_PAYLOAD)
    create = await client.post("/api/v1/patients", json=payload, headers=admin_headers)
    assert create.status_code == 201
    patient_id = create.json()["id"]
    assign = await client.post(
        f"/api/v1/patients/{patient_id}/assignments",
        headers=admin_headers,
        json={"assignee_user_id": str(doctor.id), "is_primary": False},
    )
    assert assign.status_code == 201
    return patient_id


async def create_assigned_patients_for_doctor_email(
    client: AsyncClient,
    user_repository,
    membership_repository,
    *,
    doctor_email: str,
    patient_payloads: list[dict[str, Any]],
    admin_email: str | None = None,
) -> list[str]:
    """One org, one doctor membership, multiple assigned patients (avoids multi-org membership deny)."""
    doctor = await user_repository.get_by_email(doctor_email)
    assert doctor is not None
    org_id = uuid4()
    admin = await _seed_clinic_admin(
        user_repository,
        admin_email or f"harness-ca-multi-{doctor_email}",
    )
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    await _membership(
        membership_repository,
        org_id=org_id,
        user_id=doctor.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    admin_headers = await _login(client, admin.email)
    patient_ids: list[str] = []
    for payload in patient_payloads:
        create = await client.post("/api/v1/patients", json=payload, headers=admin_headers)
        assert create.status_code == 201
        patient_id = create.json()["id"]
        assign = await client.post(
            f"/api/v1/patients/{patient_id}/assignments",
            headers=admin_headers,
            json={"assignee_user_id": str(doctor.id), "is_primary": False},
        )
        assert assign.status_code == 201
        patient_ids.append(patient_id)
    return patient_ids


async def create_assigned_patient_for_doctor_headers(
    client: AsyncClient,
    user_repository,
    membership_repository,
    doctor_headers: dict[str, str],
    *,
    patient_payload: dict[str, Any] | None = None,
    extra_org_doctor_emails: tuple[str, ...] = (),
) -> str:
    doctor_email = await doctor_email_from_headers(client, doctor_headers)
    return await create_assigned_patient_for_doctor_email(
        client,
        user_repository,
        membership_repository,
        doctor_email=doctor_email,
        patient_payload=patient_payload,
        extra_org_doctor_emails=extra_org_doctor_emails,
    )
