"""Clinical narrative endpoint tests."""

import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.application.clinical_narrative.constants import NARRATIVE_VERSION, PROMPT_VERSION
from app.core.security import hash_password
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole

PATIENT_PAYLOAD = {
    "first_name": "Narrative",
    "last_name": "Patient",
    "date_of_birth": "1985-03-10",
    "gender": "female",
}

NARRATIVE_URL = "/api/v1/patients/{patient_id}/clinical-narrative"


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    role: str = "doctor",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


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


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Clinical",
        last_name="Narrative",
        date_of_birth=date(1990, 3, 3),
        gender="male",
    )


@pytest.mark.asyncio
async def test_narrative_success_with_provenance(
    client: AsyncClient,
    patient_repository,
    medical_record_repository,
) -> None:
    headers = await _register_and_login(client, email="narr-success@example.com")
    patient_id = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"])
    doctor_id = (await patient_repository.get_by_id(patient_id)).owner_id
    await medical_record_repository.create(
        MedicalRecord(
            patient_id=patient_id,
            owner_id=doctor_id,
            record_type="visit",
            title="Endocrinology visit",
            description="Type 2 diabetes follow-up",
            diagnosis="Type 2 diabetes follow-up",
            record_date=datetime.now(UTC),
        ),
    )
    response = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={"query": "diabetes follow-up", "language": "en"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["narrative_version"] == NARRATIVE_VERSION
    assert data["prompt_version"] == PROMPT_VERSION
    assert data["language"] == "en"
    assert data["narrative"]
    assert data["disclaimer"]
    blob = json.dumps(data).lower()
    assert "securepass" not in blob


@pytest.mark.asyncio
async def test_narrative_default_overview_without_query(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="narr-default@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    response = await client.post(NARRATIVE_URL.format(patient_id=patient_id), headers=headers, json={})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_narrative_turkish_language(
    client: AsyncClient,
    patient_repository,
    medical_record_repository,
) -> None:
    headers = await _register_and_login(client, email="narr-tr@example.com")
    patient_id = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"])
    doctor_id = (await patient_repository.get_by_id(patient_id)).owner_id
    await medical_record_repository.create(
        MedicalRecord(
            patient_id=patient_id,
            owner_id=doctor_id,
            record_type="visit",
            title="Takip",
            description="Kan şekeri takibi",
            diagnosis="Kan şekeri takibi",
            record_date=datetime.now(UTC),
        ),
    )
    response = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={"language": "tr"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "tr"


@pytest.mark.asyncio
async def test_narrative_access_matrix(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "narr-owner@example.com")
    assignee = await _seed_doctor(user_repository, "narr-assignee@example.com")
    clinic_admin = await user_repository.create(
        User(
            email="narr-admin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Admin",
            last_name="User",
            role=UserRole.CLINIC_ADMIN,
        ),
    )
    other_doc = await _seed_doctor(user_repository, "narr-other-org@example.com")
    unassigned = await _seed_doctor(user_repository, "narr-unassigned@example.com")
    patient_user = await user_repository.create(
        User(
            email="narr-patient@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Pat",
            last_name="User",
            role=UserRole.PATIENT,
        ),
    )
    system_admin = await user_repository.create(
        User(
            email="narr-sys@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    legacy_patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    other_patient = await patient_repository.create(
        _patient(owner_id=other_doc.id, organization_id=None),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=assignee.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=clinic_admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=assignee.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )

    async def _login(email: str) -> dict[str, str]:
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": "securepass123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    body = {"query": "overview"}
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(assignee.email), json=body)).status_code == 200
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(clinic_admin.email), json=body)).status_code == 200
    assert (
        await client.post(
            NARRATIVE_URL.format(patient_id=legacy_patient.id),
            headers=await _login(owner.email),
            json=body,
        )
    ).status_code == 200
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(unassigned.email), json=body)).status_code == 404
    assert (await client.post(NARRATIVE_URL.format(patient_id=other_patient.id), headers=await _login(other_doc.email), json=body)).status_code == 200
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(other_doc.email), json=body)).status_code == 404
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(patient_user.email), json=body)).status_code == 403
    assert (await client.post(NARRATIVE_URL.format(patient_id=patient.id), headers=await _login(system_admin.email), json=body)).status_code == 403
