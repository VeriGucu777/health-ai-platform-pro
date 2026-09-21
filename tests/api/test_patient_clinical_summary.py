"""Deterministic patient clinical summary endpoint tests."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.application.clinical_summary.constants import SUMMARY_VERSION
from app.core.security import hash_password
from app.domain.entities.patient import Patient
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType

PATIENT_PAYLOAD = {
    "first_name": "Summary",
    "last_name": "Patient",
    "date_of_birth": "1985-03-10",
    "gender": "female",
}

SUMMARY_PATH = "/api/v1/patients/{patient_id}/clinical-summary"


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
    role: str = "doctor",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _patient(*, owner_id, organization_id=None) -> Patient:
    return Patient(
        owner_id=owner_id,
        organization_id=organization_id,
        first_name="Clinical",
        last_name="Summary",
        date_of_birth=date(1990, 3, 3),
        gender="male",
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


async def _append_risk_row(
    risk_assessment_history_repository,
    *,
    patient_id: UUID,
    evaluator_id: UUID,
    assessment_type: RiskAssessmentType,
    evaluated_at: datetime,
    probability: float | None = 0.42,
    assessment_status: str = "complete",
) -> None:
    await risk_assessment_history_repository.append(
        RiskAssessmentHistory(
            patient_id=patient_id,
            assessment_type=assessment_type,
            assessment_status=assessment_status,
            risk_level="moderate",
            score=55.0,
            probability=probability,
            model_kind=RULE_BASED_MODEL_KIND,
            model_version="rule_based_v1",
            evaluated_by_user_id=evaluator_id,
            evaluated_at=evaluated_at,
        ),
    )


@pytest.mark.asyncio
async def test_clinical_summary_content_and_provenance(
    client: AsyncClient,
    user_repository,
    risk_assessment_history_repository,
) -> None:
    headers = await _register_and_login(client, email="summary-content@example.com")
    patient_resp = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = patient_resp.json()["id"]
    owner_id = UUID(
        (await client.get(f"/api/v1/patients/{patient_id}", headers=headers)).json()["owner_id"]
    )

    record_date = datetime(2026, 5, 1, 12, 0, tzinfo=UTC).isoformat()
    record = await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "visit",
            "title": "Visit",
            "diagnosis": "Stored diagnosis text",
            "medications": "Aspirin 81mg",
        },
        headers=headers,
    )
    record_id = record.json()["id"]

    measured_at = "2026-05-02T09:00:00Z"
    measurement = await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_id,
            "measured_at": measured_at,
            "blood_glucose": 102,
            "glucose_context": "fasting",
        },
        headers=headers,
    )
    measurement_id = measurement.json()["id"]

    appt_date = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    appointment = await client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "appointment_date": appt_date,
            "appointment_type": "follow_up",
            "status": "scheduled",
        },
        headers=headers,
    )
    appointment_id = appointment.json()["id"]

    pid = UUID(patient_id)
    await _append_risk_row(
        risk_assessment_history_repository,
        patient_id=pid,
        evaluator_id=owner_id,
        assessment_type=RiskAssessmentType.DIABETES,
        evaluated_at=datetime(2026, 4, 1, tzinfo=UTC),
        probability=None,
    )
    await _append_risk_row(
        risk_assessment_history_repository,
        patient_id=pid,
        evaluator_id=owner_id,
        assessment_type=RiskAssessmentType.DIABETES,
        evaluated_at=datetime(2026, 6, 1, tzinfo=UTC),
        probability=0.31,
    )
    await _append_risk_row(
        risk_assessment_history_repository,
        patient_id=pid,
        evaluator_id=owner_id,
        assessment_type=RiskAssessmentType.HEART_DISEASE,
        evaluated_at=datetime(2026, 6, 2, tzinfo=UTC),
    )
    await _append_risk_row(
        risk_assessment_history_repository,
        patient_id=pid,
        evaluator_id=owner_id,
        assessment_type=RiskAssessmentType.STROKE,
        evaluated_at=datetime(2026, 6, 3, tzinfo=UTC),
    )

    response = await client.get(SUMMARY_PATH.format(patient_id=patient_id), headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["summary_version"] == SUMMARY_VERSION
    assert data["data_quality"]["no_data"] is False

    diagnosis_items = [i for i in data["clinical_items"] if i["item_type"] == "diagnosis"]
    assert len(diagnosis_items) == 1
    assert diagnosis_items[0]["detail"] == "Stored diagnosis text"
    assert diagnosis_items[0]["provenance"]["source_id"] == record_id

    glucose = next(m for m in data["recent_measurements"] if m["metric_type"] == "blood_glucose")
    assert glucose["value"] == "102"
    assert glucose["provenance"]["source_id"] == measurement_id

    enc = next(e for e in data["encounters"] if e["appointment_id"] == appointment_id)
    assert enc["status"] == "scheduled"
    assert enc["timing"] == "future"

    diabetes = next(r for r in data["latest_risk_assessments"] if r["assessment_type"] == "diabetes")
    assert diabetes["probability"] == 0.31
    assert diabetes["provenance"]["source_type"] == "risk_assessment_history"

    older_diabetes_prob = [
        r for r in data["latest_risk_assessments"] if r.get("probability") is None and r["assessment_type"] == "diabetes"
    ]
    assert len(older_diabetes_prob) == 0


@pytest.mark.asyncio
async def test_clinical_summary_empty_data_quality_not_normal(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(client, email="summary-empty@example.com")
    patient_id = (
        await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    ).json()["id"]

    response = await client.get(SUMMARY_PATH.format(patient_id=patient_id), headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data_quality"]["no_data"] is True
    assert "clinical_items" in data["data_quality"]["missing_sections"]
    assert any(f["flag_type"] == "missing_recent_measurement" for f in data["care_flags"])


@pytest.mark.asyncio
async def test_clinical_summary_deterministic_excluding_generated_at(
    client: AsyncClient,
    risk_assessment_history_repository,
) -> None:
    headers = await _register_and_login(client, email="summary-determ@example.com")
    patient_id = (
        await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    ).json()["id"]

    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": patient_id,
            "record_date": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            "record_type": "visit",
            "title": "Stable",
            "diagnosis": "Same",
        },
        headers=headers,
    )

    first = await client.get(SUMMARY_PATH.format(patient_id=patient_id), headers=headers)
    second = await client.get(SUMMARY_PATH.format(patient_id=patient_id), headers=headers)
    assert first.status_code == 200 and second.status_code == 200

    body1 = dict(first.json())
    body2 = dict(second.json())
    body1.pop("generated_at")
    body2.pop("generated_at")
    assert body1 == body2


@pytest.mark.asyncio
async def test_clinical_summary_invalid_date_range_422(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="summary-range@example.com")
    patient_id = (
        await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    ).json()["id"]
    date_from = datetime.now(UTC).isoformat()
    date_to = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = await client.get(
        SUMMARY_PATH.format(patient_id=patient_id),
        params={"date_from": date_from, "date_to": date_to},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assigned_doctor_clinical_summary_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "sum-assign-owner@example.com")
    assignee = await _seed_doctor(user_repository, "sum-assign-doc@example.com")
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
    headers = await _login(client, assignee.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_clinic_admin_clinical_summary_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "sum-ca-owner@example.com")
    admin = await user_repository.create(
        User(
            email="sum-ca-admin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="A",
            last_name="D",
            role=UserRole.CLINIC_ADMIN,
        ),
    )
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, admin.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_legacy_owner_clinical_summary_200(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    owner = await _seed_doctor(user_repository, "sum-legacy-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    headers = await _login(client, owner.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 200


@pytest.mark.asyncio
async def test_unassigned_same_org_clinical_summary_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_id = uuid4()
    owner = await _seed_doctor(user_repository, "sum-unassigned-owner@example.com")
    other = await _seed_doctor(user_repository, "sum-unassigned-doc@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_id))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=other.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, other.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_cross_org_clinical_summary_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
) -> None:
    org_a, org_b = uuid4(), uuid4()
    owner = await _seed_doctor(user_repository, "sum-cross-owner@example.com")
    outsider = await _seed_doctor(user_repository, "sum-cross-outsider@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=org_a))
    await membership_repository.create(
        OrganizationMembership(
            organization_id=org_b,
            user_id=outsider.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    headers = await _login(client, outsider.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_inactive_patient_clinical_summary_404(
    client: AsyncClient,
    user_repository,
    patient_repository,
) -> None:
    owner = await _seed_doctor(user_repository, "sum-inactive-owner@example.com")
    patient = await patient_repository.create(_patient(owner_id=owner.id, organization_id=None))
    patient.is_active = False
    await patient_repository.update(patient)
    headers = await _login(client, owner.email)
    assert (
        await client.get(SUMMARY_PATH.format(patient_id=patient.id), headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_patient_role_clinical_summary_403(client: AsyncClient) -> None:
    headers = await _register_and_login(
        client,
        email="summary-patient-role@example.com",
        role="patient",
    )
    pid = "00000000-0000-4000-8000-000000000099"
    assert (await client.get(SUMMARY_PATH.format(patient_id=pid), headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_system_admin_clinical_summary_403(
    client: AsyncClient,
    user_repository,
) -> None:
    admin = await user_repository.create(
        User(
            email="sum-sysadmin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    headers = await _login(client, admin.email)
    pid = "00000000-0000-4000-8000-000000000088"
    assert (await client.get(SUMMARY_PATH.format(patient_id=pid), headers=headers)).status_code == 403
