"""Clinical encounter HTTP API integration tests."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.api.deps import get_clinical_encounter_service
from app.core.config import Settings
from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditResourceType

from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.support.clinical_encounter_service_factory import build_clinical_encounter_service
from tests.support.org_assigned_patient_harness import (
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
    register_clinic_admin_and_login,
)

_FINALIZE_SECTIONS = [
    {"section_key": "assessment", "content_key": "stable", "clinician_text": "Stable for pilot."},
]


async def _create_encounter(
    client: AsyncClient,
    headers: dict[str, str],
    patient_id: str,
    *,
    specialty_key: str = "cardiology",
) -> dict:
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
        json={"specialty_key": specialty_key, "locale": "en"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _encounter_audit_rows(audit_log_repository) -> list:
    return [
        row
        for row in audit_log_repository.list_all()
        if row.resource_type == AuditResourceType.CLINICAL_ENCOUNTER
    ]


@pytest.mark.asyncio
async def test_assigned_doctor_creates_encounter_201(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-create@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    data = await _create_encounter(client, headers, patient_id)
    assert data["encounter"]["status"] == "active"
    assert data["encounter"]["specialty_key"] == "cardiology"
    assert data["encounter"]["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_unassigned_doctor_create_returns_404(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_headers = await register_and_login_doctor(client, email="enc-owner@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        owner_headers,
    )
    outsider_headers = await register_and_login_doctor(client, email="enc-outsider@example.com")
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=outsider_headers,
        json={"specialty_key": "cardiology", "locale": "en"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_second_active_encounter_returns_409(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-dup@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    await _create_encounter(client, headers, patient_id)
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
        json={"specialty_key": "cardiology", "locale": "en"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_rejects_spoofed_server_fields(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-spoof@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
        json={
            "specialty_key": "cardiology",
            "locale": "en",
            "clinician_user_id": str(uuid4()),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_consent_blocks_create(
    client: AsyncClient,
    app,
    user_repository,
    membership_repository,
    patient_repository,
    assignment_repository,
    consent_repository,
    clinical_encounter_repository,
    audit_log_repository,
    test_settings: Settings,
) -> None:
    enforced = test_settings.model_copy(update={"clinical_consent_enforced": True})

    def override_encounter(_request: Request):
        return build_clinical_encounter_service(
            encounter_repository=clinical_encounter_repository,
            patient_repository=patient_repository,
            membership_repository=membership_repository,
            assignment_repository=assignment_repository,
            settings=enforced,
            consent_repository=consent_repository,
            audit_log_repository=audit_log_repository,
        )

    app.dependency_overrides[get_clinical_encounter_service] = override_encounter
    headers = await register_and_login_doctor(client, email="enc-consent@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    before_encounters = len(clinical_encounter_repository._aggregates)
    before_audit = len(_encounter_audit_rows(audit_log_repository))
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
        json={"specialty_key": "cardiology", "locale": "en"},
    )
    assert response.status_code == 403, response.text
    assert len(clinical_encounter_repository._aggregates) == before_encounters
    assert len(_encounter_audit_rows(audit_log_repository)) == before_audit


@pytest.mark.asyncio
async def test_list_and_get_encounter(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-list@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    created = await _create_encounter(client, headers, patient_id)
    encounter_id = created["encounter"]["id"]

    list_response = await client.get(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == encounter_id
    assert "complaints" not in listed["items"][0]

    get_response = await client.get(f"/api/v1/encounters/{encounter_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["encounter"]["id"] == encounter_id


@pytest.mark.asyncio
async def test_list_emits_single_encounter_audit(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-list-audit@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    await _create_encounter(client, headers, patient_id)
    before = len(_encounter_audit_rows(audit_log_repository))
    response = await client.get(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
    )
    assert response.status_code == 200
    after = _encounter_audit_rows(audit_log_repository)
    assert len(after) == before + 1
    assert after[-1].action == AuditAction.LIST


@pytest.mark.asyncio
async def test_assigned_peer_can_read_but_not_mutate(
    client: AsyncClient,
    user_repository,
    membership_repository,
    assignment_repository,
    patient_repository,
) -> None:
    owner_headers = await register_and_login_doctor(client, email="enc-owner2@example.com")
    peer_headers = await register_and_login_doctor(
        client,
        email="enc-peer@example.com",
    )
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        extra_org_doctor_emails=("enc-peer@example.com",),
    )
    patient = await patient_repository.get_by_id(UUID(patient_id))
    peer = await user_repository.get_by_email("enc-peer@example.com")
    assert patient is not None and peer is not None
    await assignment_repository.create(
        PatientAssignment(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            assignee_user_id=peer.id,
            is_primary=False,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    created = await _create_encounter(client, owner_headers, patient_id)
    encounter_id = created["encounter"]["id"]

    read_response = await client.get(f"/api/v1/encounters/{encounter_id}", headers=peer_headers)
    assert read_response.status_code == 200

    mutate = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=peer_headers,
        json={"complaint_key": "chest_pain"},
    )
    assert mutate.status_code == 404


@pytest.mark.asyncio
async def test_complaint_finding_question_finalize_cancel_flow(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-flow@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    created = await _create_encounter(client, headers, patient_id)
    encounter_id = created["encounter"]["id"]
    version = created["encounter"]["version"]

    complaint = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=headers,
        json={"complaint_key": "chest_pain", "is_primary": True},
    )
    assert complaint.status_code == 201

    invalid_complaint = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=headers,
        json={},
    )
    assert invalid_complaint.status_code == 422

    finding = await client.post(
        f"/api/v1/encounters/{encounter_id}/findings",
        headers=headers,
        json={"finding_type": "symptom", "finding_key": "dyspnea"},
    )
    assert finding.status_code == 201

    invalid_finding = await client.post(
        f"/api/v1/encounters/{encounter_id}/findings",
        headers=headers,
        json={"finding_type": "symptom", "finding_key": "bp", "value_numeric": "120"},
    )
    assert invalid_finding.status_code == 422

    question = await client.put(
        f"/api/v1/encounters/{encounter_id}/question-responses/q1",
        headers=headers,
        json={"answer_type": "boolean", "answer_code": "yes"},
    )
    assert question.status_code == 200

    question_update = await client.put(
        f"/api/v1/encounters/{encounter_id}/question-responses/q1",
        headers=headers,
        json={"answer_type": "boolean", "answer_code": "no"},
    )
    assert question_update.status_code == 200

    detail = await client.get(f"/api/v1/encounters/{encounter_id}", headers=headers)
    version = detail.json()["encounter"]["version"]
    complaint_id = detail.json()["complaints"][0]["id"]

    stale_finalize = await client.post(
        f"/api/v1/encounters/{encounter_id}/finalize",
        headers=headers,
        json={"expected_version": version - 1, "summary_sections": _FINALIZE_SECTIONS},
    )
    assert stale_finalize.status_code == 409

    finalize = await client.post(
        f"/api/v1/encounters/{encounter_id}/finalize",
        headers=headers,
        json={"expected_version": version, "summary_sections": _FINALIZE_SECTIONS},
    )
    assert finalize.status_code == 200
    assert finalize.json()["final_summary"] is not None
    assert finalize.json()["final_summary"]["summary_sections"]

    repeat_finalize = await client.post(
        f"/api/v1/encounters/{encounter_id}/finalize",
        headers=headers,
        json={"expected_version": finalize.json()["encounter"]["version"], "summary_sections": _FINALIZE_SECTIONS},
    )
    assert repeat_finalize.status_code == 409

    deactivate = await client.delete(
        f"/api/v1/encounters/{encounter_id}/complaints/{complaint_id}",
        headers=headers,
    )
    assert deactivate.status_code == 409

    audit_rows = _encounter_audit_rows(audit_log_repository)
    operations = {(row.metadata or {}).get("operation") for row in audit_rows}
    assert "encounter_created" in operations
    assert "encounter_viewed" in operations
    assert "encounter_finalized" in operations
    serialized = json.dumps([{"metadata": row.metadata} for row in audit_rows])
    assert "Stable for pilot" not in serialized


@pytest.mark.asyncio
async def test_cancel_encounter(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-cancel@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    created = await _create_encounter(client, headers, patient_id)
    encounter_id = created["encounter"]["id"]
    version = created["encounter"]["version"]
    response = await client.post(
        f"/api/v1/encounters/{encounter_id}/cancel",
        headers=headers,
        json={"expected_version": version},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_deactivate_complaint_on_active_encounter(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="enc-deact@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    created = await _create_encounter(client, headers, patient_id)
    encounter_id = created["encounter"]["id"]
    complaint = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=headers,
        json={"complaint_key": "cough"},
    )
    complaint_id = complaint.json()["id"]
    response = await client.delete(
        f"/api/v1/encounters/{encounter_id}/complaints/{complaint_id}",
        headers=headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_clinic_admin_and_system_admin_cannot_mutate(
    client: AsyncClient,
    user_repository,
    membership_repository,
    patient_repository,
) -> None:
    doctor_headers = await register_and_login_doctor(client, email="enc-doc-admin@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        doctor_headers,
    )
    created = await _create_encounter(client, doctor_headers, patient_id)
    encounter_id = created["encounter"]["id"]

    admin_headers, _, _ = await register_clinic_admin_and_login(
        client,
        user_repository,
        membership_repository,
        email="enc-ca@example.com",
    )

    ca_mutate = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=admin_headers,
        json={"complaint_key": "pain"},
    )
    assert ca_mutate.status_code in (403, 404)

    patient = await patient_repository.get_by_id(UUID(patient_id))
    assert patient is not None
    await membership_repository.create(
        OrganizationMembership(
            organization_id=patient.organization_id,
            user_id=(await user_repository.get_by_email("enc-ca@example.com")).id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )

    sys_admin = await user_repository.create(
        User(
            email="enc-sys@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    await membership_repository.create(
        OrganizationMembership(
            organization_id=patient.organization_id,
            user_id=sys_admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "enc-sys@example.com", "password": "securepass123"},
    )
    sys_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    sys_mutate = await client.post(
        f"/api/v1/encounters/{encounter_id}/complaints",
        headers=sys_headers,
        json={"complaint_key": "pain"},
    )
    assert sys_mutate.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/encounters/{uuid4()}")
    assert response.status_code == 401
