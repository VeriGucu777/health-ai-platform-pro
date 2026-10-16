"""Clinical Copilot evaluate endpoint — technical scaffold tests."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.api.deps import get_clinical_copilot_evaluation_service, get_clinical_encounter_service
from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.clinical_decision.enums import EvaluationStatus
from app.domain.entities.patient import Patient
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from tests.support.clinical_copilot_evaluation_service_factory import (
    build_clinical_copilot_evaluation_service,
)
from tests.support.clinical_encounter_service_factory import build_clinical_encounter_service
from tests.support.org_assigned_patient_harness import (
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
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


async def _evaluate(
    client: AsyncClient,
    headers: dict[str, str],
    patient_id: str,
    encounter_id: str,
    *,
    context_profile: str = "hypertension_v1",
) -> dict:
    return await client.post(
        f"/api/v1/patients/{patient_id}/encounters/{encounter_id}/evaluate",
        headers=headers,
        json={"context_profile": context_profile},
    )


def _copilot_audit_rows(audit_log_repository) -> list:
    return [
        row
        for row in audit_log_repository.list_all()
        if row.resource_type == AuditResourceType.CLINICAL_ENCOUNTER
        and row.metadata
        and str(row.metadata.get("operation", "")).startswith("copilot_evaluation_")
    ]


@pytest.mark.asyncio
async def test_assigned_doctor_evaluate_succeeds_empty_outputs(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-ok@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    enc = await _create_encounter(client, headers, patient_id)
    encounter_id = enc["encounter"]["id"]

    response = await _evaluate(client, headers, patient_id, encounter_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evaluation_status"] == EvaluationStatus.NO_APPLICABLE_RULES.value
    assert body["missing_information"] == []
    assert body["review_domain_status"] == []
    assert body["documentation_reminders"] == []
    assert body["read_only"] is False
    prov = body["provenance"]
    assert prov["input_snapshot_id"]
    assert prov["context_profile"] == "hypertension_v1"
    assert prov["specialty_key"] == "cardiology"
    assert prov["engine_version"]
    assert prov["rule_provenance"] == []
    assert "differential" not in body
    assert "treatment" not in response.text.lower()

    audits = _copilot_audit_rows(audit_log_repository)
    ops = [a.metadata["operation"] for a in audits]
    assert "copilot_evaluation_requested" in ops
    assert "copilot_evaluation_succeeded" in ops
    succeeded = next(a for a in audits if a.metadata["operation"] == "copilot_evaluation_succeeded")
    assert succeeded.action == AuditAction.EXECUTE
    assert succeeded.outcome == AuditOutcome.SUCCESS
    assert succeeded.metadata.get("input_snapshot_id")


@pytest.mark.asyncio
async def test_unassigned_patient_evaluate_returns_404(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    owner_headers = await register_and_login_doctor(client, email="copilot-owner@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        owner_headers,
    )
    enc = await _create_encounter(client, owner_headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    outsider_headers = await register_and_login_doctor(client, email="copilot-outsider@example.com")
    response = await _evaluate(client, outsider_headers, patient_id, encounter_id)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cross_organization_evaluate_returns_404_no_resource_leak(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
    audit_log_repository,
) -> None:
    """Clinician in org B must not evaluate org A patient/encounter (404 masking)."""
    org_a = uuid4()
    org_b = uuid4()
    owner = await user_repository.create(
        User(
            email="copilot-orga-owner@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="OrgA",
            last_name="Owner",
            role=UserRole.DOCTOR,
        ),
    )
    cross_org_doctor = await user_repository.create(
        User(
            email="copilot-orgb-cross@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="OrgB",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )
    patient = await patient_repository.create(
        Patient(
            owner_id=owner.id,
            organization_id=org_a,
            first_name="CrossOrg",
            last_name="Patient",
            date_of_birth=date(1988, 3, 3),
            gender="female",
        ),
    )
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
            user_id=cross_org_doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_a,
            patient_id=patient.id,
            assignee_user_id=owner.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )

    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": owner.email, "password": "securepass123"},
    )
    assert owner_login.status_code == 200
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    cross_login = await client.post(
        "/api/v1/auth/login",
        json={"email": cross_org_doctor.email, "password": "securepass123"},
    )
    assert cross_login.status_code == 200
    cross_headers = {"Authorization": f"Bearer {cross_login.json()['access_token']}"}

    patient_id = str(patient.id)
    enc = await _create_encounter(client, owner_headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    organization_id = enc["encounter"]["organization_id"]

    audits_before = len(_copilot_audit_rows(audit_log_repository))
    response = await _evaluate(client, cross_headers, patient_id, encounter_id)
    assert response.status_code == 404
    payload = response.json()
    assert payload.get("success") is False
    body_text = response.text.lower()
    assert str(org_a) not in response.text
    assert str(org_b) not in response.text
    assert organization_id not in response.text
    assert patient_id not in response.text
    assert encounter_id not in response.text
    assert "crossorg" not in body_text
    assert "evaluation_id" not in body_text
    assert "provenance" not in body_text
    audits_after = _copilot_audit_rows(audit_log_repository)
    assert len(audits_after) == audits_before
    assert not any(row.metadata.get("operation") == "copilot_evaluation_succeeded" for row in audits_after)


@pytest.mark.asyncio
async def test_cross_patient_encounter_path_returns_404(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-cross-p@example.com")
    from tests.support.org_assigned_patient_harness import create_assigned_patients_for_doctor_email
    from tests.support.patient_test_constants import PATIENT_PAYLOAD

    doctor_email = (await client.get("/api/v1/auth/me", headers=headers)).json()["email"]
    alt_payload = {**PATIENT_PAYLOAD, "first_name": "Other", "last_name": "Patient"}
    patient_a, patient_b = await create_assigned_patients_for_doctor_email(
        client,
        user_repository,
        membership_repository,
        doctor_email=doctor_email,
        patient_payloads=[PATIENT_PAYLOAD, alt_payload],
    )
    enc = await _create_encounter(client, headers, patient_a)
    encounter_id = enc["encounter"]["id"]
    response = await _evaluate(client, headers, patient_b, encounter_id)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_encounter_returns_404(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-missing-enc@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    response = await _evaluate(client, headers, patient_id, str(uuid4()))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_finalized_encounter_evaluate_read_only(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-final@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    enc = await _create_encounter(client, headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    fin = await client.post(
        f"/api/v1/encounters/{encounter_id}/finalize",
        headers=headers,
        json={"expected_version": enc["encounter"]["version"], "summary_sections": _FINALIZE_SECTIONS},
    )
    assert fin.status_code == 200, fin.text

    response = await _evaluate(client, headers, patient_id, encounter_id)
    assert response.status_code == 200, response.text
    assert response.json()["read_only"] is True


@pytest.mark.asyncio
async def test_draft_encounter_evaluate_unavailable_409(
    client: AsyncClient,
    user_repository,
    membership_repository,
    clinical_encounter_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-draft@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    enc = await _create_encounter(client, headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    from app.domain.clinical_encounter.enums import EncounterStatus

    aggregate = await clinical_encounter_repository.get_by_id(UUID(encounter_id))
    assert aggregate is not None
    aggregate.encounter.status = EncounterStatus.DRAFT
    await clinical_encounter_repository.save(aggregate)

    response = await _evaluate(client, headers, patient_id, encounter_id)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_unauthenticated_evaluate_401(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/patients/{uuid4()}/encounters/{uuid4()}/evaluate",
        json={"context_profile": "hypertension_v1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_clinical_role_denied(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    from app.core.security import hash_password
    from app.domain.entities.user import User

    doctor_headers = await register_and_login_doctor(client, email="copilot-doc-sys@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        doctor_headers,
    )
    enc = await _create_encounter(client, doctor_headers, patient_id)
    encounter_id = enc["encounter"]["id"]

    await user_repository.create(
        User(
            email="copilot-sys@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "copilot-sys@example.com", "password": "securepass123"},
    )
    sys_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await _evaluate(client, sys_headers, patient_id, encounter_id)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_context_profile_422(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-bad-profile@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    enc = await _create_encounter(client, headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    response = await _evaluate(
        client,
        headers,
        patient_id,
        encounter_id,
        context_profile="unknown_profile",
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_cardiology_specialty_with_hypertension_profile_422(
    client: AsyncClient,
    user_repository,
    membership_repository,
    clinical_encounter_repository,
) -> None:
    headers = await register_and_login_doctor(client, email="copilot-wrong-spec@example.com")
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    enc = await _create_encounter(client, headers, patient_id)
    encounter_id = enc["encounter"]["id"]
    aggregate = await clinical_encounter_repository.get_by_id(UUID(encounter_id))
    assert aggregate is not None
    aggregate.encounter.specialty_key = "internal_medicine"
    await clinical_encounter_repository.save(aggregate)
    response = await _evaluate(client, headers, patient_id, encounter_id)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_malformed_uuid_path_422(client: AsyncClient) -> None:
    headers = await register_and_login_doctor(client, email="copilot-malformed@example.com")
    response = await client.post(
        "/api/v1/patients/not-a-uuid/encounters/not-a-uuid/evaluate",
        headers=headers,
        json={"context_profile": "hypertension_v1"},
    )
    assert response.status_code == 422
