"""Patient clinical retrieval (RAG v1) endpoint tests."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.application.clinical_retrieval.constants import RETRIEVAL_VERSION
from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole

RETRIEVAL_URL = "/api/v1/patients/{patient_id}/clinical-retrieval"
PATIENT_PAYLOAD = {
    "first_name": "Retrieval",
    "last_name": "Patient",
    "date_of_birth": "1988-01-01",
    "gender": "female",
}


async def _register_and_login(client: AsyncClient, email: str, role: str = "doctor") -> dict[str, str]:
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
    token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "securepass123"})).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="R",
        last_name="P",
        date_of_birth=date(1990, 1, 1),
        gender="male",
    )


async def _seed_doctor(user_repository, email: str) -> User:
    return await user_repository.create(
        User(
            email=email,
            hashed_password=hash_password("securepass123"),
            first_name="D",
            last_name="R",
            role=UserRole.DOCTOR,
        ),
    )


@pytest.mark.asyncio
async def test_retrieval_returns_provenance_and_version(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="retr-happy@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    record_date = datetime(2026, 5, 1, tzinfo=UTC).isoformat()
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "visit",
            "title": "Visit",
            "diagnosis": "Stored hypertension for retrieval",
        },
        headers=headers,
    )
    response = await client.post(
        RETRIEVAL_URL.format(patient_id=patient_id),
        headers=headers,
        json={"query": "hypertension retrieval", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["retrieval_version"] == RETRIEVAL_VERSION
    assert data["query_received"] is True
    assert len(data["results"]) >= 1
    hit = data["results"][0]
    assert hit["evidence_id"].startswith("medical_record:")
    assert hit["source_type"] == "medical_record"
    assert "diagnosis" in hit["content_fields"] or "Stored" in str(hit["content_fields"])


@pytest.mark.asyncio
async def test_retrieval_empty_query_422(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="retr-empty@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    response = await client.post(
        RETRIEVAL_URL.format(patient_id=patient_id),
        headers=headers,
        json={"query": "   "},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_retrieval_deterministic_ordering(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="retr-order@example.com")
    patient_id = (await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"]
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "record_type": "visit",
            "title": "A",
            "diagnosis": "alpha condition",
        },
        headers=headers,
    )
    body = {"query": "alpha condition", "top_k": 5}
    r1 = await client.post(RETRIEVAL_URL.format(patient_id=patient_id), headers=headers, json=body)
    r2 = await client.post(RETRIEVAL_URL.format(patient_id=patient_id), headers=headers, json=body)
    assert r1.json()["results"] == r2.json()["results"]


@pytest.mark.asyncio
async def test_assigned_doctor_retrieval_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "retr-assign-owner@example.com")
    assignee = await _seed_doctor(user_repository, "retr-assign-doc@example.com")
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
            status=AssignmentStatus.ACTIVE,
        ),
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": assignee.email, "password": "securepass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.post(
        RETRIEVAL_URL.format(patient_id=patient.id),
        headers=headers,
        json={"query": "care"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unassigned_retrieval_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "retr-unas-owner@example.com")
    other = await _seed_doctor(user_repository, "retr-unas-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=other.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    login = await client.post("/api/v1/auth/login", json={"email": other.email, "password": "securepass123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (
        await client.post(
            RETRIEVAL_URL.format(patient_id=patient.id),
            headers=headers,
            json={"query": "test"},
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_patient_role_retrieval_403(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="retr-patient@example.com", role="patient")
    pid = "00000000-0000-4000-8000-000000000099"
    assert (
        await client.post(RETRIEVAL_URL.format(patient_id=pid), headers=headers, json={"query": "x"})
    ).status_code == 403
