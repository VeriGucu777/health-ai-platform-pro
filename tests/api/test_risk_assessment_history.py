"""Risk assessment history — append on execute, list under READ policy."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import PatientAssignment
from app.domain.organization.enums import AssignmentStatus, OrganizationMembershipRole
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from tests.api.test_child_resource_policy import (
    _login,
    _membership,
    _patient,
    _seed_clinic_admin,
    _seed_doctor,
)
from tests.support.risk_assessment_test_helpers import ASSESSMENT_DATE_RANGE, create_measurement

HISTORY_URL = "/api/v1/patients/{patient_id}/risk-assessments/history"


@pytest.fixture
async def history_setup(
    client: AsyncClient,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
):
    org_a = uuid4()
    owner = await _seed_doctor(user_repository, "hist-owner@example.com")
    assigned = await _seed_doctor(user_repository, "hist-assigned@example.com")
    unassigned = await _seed_doctor(user_repository, "hist-unassigned@example.com")
    cross_org = await _seed_doctor(user_repository, "hist-cross@example.com")
    clinic_admin = await _seed_clinic_admin(user_repository, "hist-ca@example.com")
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
        org_id=org_a,
        user_id=clinic_admin.id,
        role=OrganizationMembershipRole.CLINIC_ADMIN,
    )
    await _membership(
        membership_repository,
        org_id=uuid4(),
        user_id=cross_org.id,
        role=OrganizationMembershipRole.DOCTOR,
    )
    await assignment_repository.create(
        PatientAssignment(
            organization_id=org_a,
            patient_id=patient.id,
            assignee_user_id=assigned.id,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    return {
        "org_a": org_a,
        "patient_id": str(patient.id),
        "owner_headers": await _login(client, owner.email),
        "assigned_headers": await _login(client, assigned.email),
        "unassigned_headers": await _login(client, unassigned.email),
        "cross_headers": await _login(client, cross_org.email),
        "admin_headers": await _login(client, clinic_admin.email),
    }


async def _seed_vitals(client: AsyncClient, headers: dict[str, str], patient_id: str) -> None:
    await create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=95,
        glucose_context="fasting",
        systolic_pressure=118,
        diastolic_pressure=76,
        heart_rate=72,
    )


@pytest.mark.asyncio
async def test_each_risk_run_appends_one_history_row(
    client: AsyncClient,
    history_setup,
    risk_assessment_history_repository,
) -> None:
    headers = history_setup["owner_headers"]
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, headers, patient_id)

    for path in (
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{patient_id}/risk-assessments/heart-disease?{ASSESSMENT_DATE_RANGE}",
        f"/api/v1/patients/{patient_id}/risk-assessments/stroke?{ASSESSMENT_DATE_RANGE}",
    ):
        assert (await client.get(path, headers=headers)).status_code == 200

    rows = risk_assessment_history_repository.rows
    assert len(rows) == 3
    types = {row.assessment_type for row in rows}
    assert types == {
        RiskAssessmentType.DIABETES,
        RiskAssessmentType.HEART_DISEASE,
        RiskAssessmentType.STROKE,
    }
    for row in rows:
        assert row.model_kind == RULE_BASED_MODEL_KIND
        assert row.probability is None
        assert row.result_snapshot is not None
        assert "contributing_factors" in row.result_snapshot
        assert "missing_inputs" in row.result_snapshot
        assert "recommendations" in row.result_snapshot


@pytest.mark.asyncio
async def test_single_assessment_call_creates_one_history_row(
    client: AsyncClient,
    history_setup,
    risk_assessment_history_repository,
) -> None:
    headers = history_setup["owner_headers"]
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, headers, patient_id)
    url = f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}"
    assert (await client.get(url, headers=headers)).status_code == 200
    assert (await client.get(url, headers=headers)).status_code == 200
    diabetes_rows = [
        r
        for r in risk_assessment_history_repository.rows
        if r.assessment_type == RiskAssessmentType.DIABETES
    ]
    assert len(diabetes_rows) == 2


@pytest.mark.asyncio
async def test_failed_assessment_does_not_append_history(
    client: AsyncClient,
    history_setup,
    risk_assessment_history_repository,
) -> None:
    headers = history_setup["owner_headers"]
    patient_id = history_setup["patient_id"]
    bad_range = "date_from=2026-09-01T00:00:00Z&date_to=2026-08-01T00:00:00Z"
    url = f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{bad_range}"
    assert (await client.get(url, headers=headers)).status_code == 422
    assert len(risk_assessment_history_repository.rows) == 0


@pytest.mark.asyncio
async def test_history_list_newest_first_and_type_filter(
    client: AsyncClient,
    history_setup,
) -> None:
    headers = history_setup["assigned_headers"]
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, history_setup["owner_headers"], patient_id)
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        headers=headers,
    )
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/stroke?{ASSESSMENT_DATE_RANGE}",
        headers=headers,
    )
    listing = await client.get(
        HISTORY_URL.format(patient_id=patient_id),
        headers=headers,
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["evaluated_at"] >= body["items"][1]["evaluated_at"]

    filtered = await client.get(
        HISTORY_URL.format(patient_id=patient_id) + "?assessment_type=diabetes",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["assessment_type"] == "diabetes"


@pytest.mark.asyncio
async def test_history_read_authorization_matrix(
    client: AsyncClient,
    history_setup,
) -> None:
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, history_setup["owner_headers"], patient_id)
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        headers=history_setup["owner_headers"],
    )
    url = HISTORY_URL.format(patient_id=patient_id)
    assert (await client.get(url, headers=history_setup["assigned_headers"])).status_code == 200
    assert (await client.get(url, headers=history_setup["admin_headers"])).status_code == 200
    assert (await client.get(url, headers=history_setup["unassigned_headers"])).status_code == 404
    assert (await client.get(url, headers=history_setup["cross_headers"])).status_code == 404


@pytest.mark.asyncio
async def test_patient_and_system_admin_forbidden_on_history(
    client: AsyncClient,
    user_repository,
    history_setup,
) -> None:
    patient_user = await user_repository.create(
        User(
            email="hist-pat@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Pat",
            last_name="User",
            role=UserRole.PATIENT,
        ),
    )
    sys_admin = await user_repository.create(
        User(
            email="hist-sys@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        ),
    )
    pat_headers = await _login(client, patient_user.email)
    sys_headers = await _login(client, sys_admin.email)
    url = HISTORY_URL.format(patient_id=history_setup["patient_id"])
    assert (await client.get(url, headers=pat_headers)).status_code == 403
    assert (await client.get(url, headers=sys_headers)).status_code == 403


@pytest.mark.asyncio
async def test_soft_deleted_patient_history_api_404_rows_persist(
    client: AsyncClient,
    history_setup,
    risk_assessment_history_repository,
) -> None:
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, history_setup["owner_headers"], patient_id)
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        headers=history_setup["owner_headers"],
    )
    before = len(risk_assessment_history_repository.rows)
    assert before == 1
    assert (
        await client.delete(
            f"/api/v1/patients/{patient_id}",
            headers=history_setup["admin_headers"],
        )
    ).status_code == 204
    url = HISTORY_URL.format(patient_id=patient_id)
    assert (await client.get(url, headers=history_setup["admin_headers"])).status_code == 404
    assert len(risk_assessment_history_repository.rows) == before


@pytest.mark.asyncio
async def test_history_read_audit_phi_safe(
    client: AsyncClient,
    history_setup,
    audit_log_repository,
) -> None:
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, history_setup["owner_headers"], patient_id)
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        headers=history_setup["owner_headers"],
    )
    await client.get(
        HISTORY_URL.format(patient_id=patient_id) + "?page=1&page_size=10&assessment_type=diabetes",
        headers=history_setup["assigned_headers"],
    )
    list_audits = [
        a
        for a in audit_log_repository.list_all()
        if a.resource_type == AuditResourceType.RISK_ASSESSMENT
        and a.action == AuditAction.LIST
        and a.outcome.value == "success"
    ]
    assert list_audits
    meta = list_audits[-1].metadata or {}
    assert meta.get("risk_kind") == "history"
    assert meta.get("page") == 1
    assert meta.get("assessment_type") == "diabetes"
    assert "score" not in meta
    assert "risk_level" not in meta


@pytest.mark.asyncio
async def test_repository_has_no_public_update_or_delete() -> None:
    from app.infrastructure.repositories.risk_assessment_history_repository import (
        SQLAlchemyRiskAssessmentHistoryRepository,
    )

    assert not hasattr(SQLAlchemyRiskAssessmentHistoryRepository, "update")
    assert not hasattr(SQLAlchemyRiskAssessmentHistoryRepository, "delete")


@pytest.mark.asyncio
async def test_diabetes_model_version_in_history(
    client: AsyncClient,
    history_setup,
    risk_assessment_history_repository,
) -> None:
    headers = history_setup["owner_headers"]
    patient_id = history_setup["patient_id"]
    await _seed_vitals(client, headers, patient_id)
    await client.get(
        f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}",
        headers=headers,
    )
    row = risk_assessment_history_repository.rows[0]
    assert row.model_version == "rule_based_v1"
