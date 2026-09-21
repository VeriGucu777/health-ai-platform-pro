"""Risk assessment audit integration tests."""

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from tests.support.risk_assessment_test_helpers import (
    ASSESSMENT_DATE_RANGE,
    create_measurement,
    create_patient,
    register_and_login,
)
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository

DIABETES_URL = "/api/v1/patients/{patient_id}/risk-assessments/diabetes?{date_range}"
HEART_URL = "/api/v1/patients/{patient_id}/risk-assessments/heart-disease?{date_range}"
STROKE_URL = "/api/v1/patients/{patient_id}/risk-assessments/stroke?{date_range}"


def _risk_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [
        record
        for record in repo.list_all()
        if record.resource_type == AuditResourceType.RISK_ASSESSMENT
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url_template", "risk_kind", "email"),
    [
        (DIABETES_URL, "diabetes", "ra-audit-diabetes@example.com"),
        (HEART_URL, "heart_disease", "ra-audit-heart@example.com"),
        (STROKE_URL, "stroke", "ra-audit-stroke@example.com"),
    ],
)
async def test_risk_assessment_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    url_template: str,
    risk_kind: str,
    email: str,
) -> None:
    headers = await register_and_login(client, email=email)
    patient_id = await create_patient(client, headers)
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
    audit_log_repository.records.clear()

    url = url_template.format(patient_id=patient_id, date_range=ASSESSMENT_DATE_RANGE)
    response = await client.get(url, headers=headers)
    assert response.status_code == 200

    events = _risk_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.EXECUTE
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == UUID(patient_id)
    assert event.metadata == {"risk_kind": risk_kind}


@pytest.mark.asyncio
async def test_risk_audit_metadata_excludes_clinical_scores(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await register_and_login(client, email="ra-audit-phi@example.com")
    patient_id = await create_patient(client, headers)
    await create_measurement(
        client,
        headers,
        patient_id=patient_id,
        measured_at="2026-08-10T08:00:00Z",
        blood_glucose=180,
        glucose_context="fasting",
        systolic_pressure=150,
        diastolic_pressure=95,
        heart_rate=88,
    )
    audit_log_repository.records.clear()

    url = DIABETES_URL.format(patient_id=patient_id, date_range=ASSESSMENT_DATE_RANGE)
    response = await client.get(url, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body.get("score") is not None or body.get("risk_level") is not None

    serialized = json.dumps([record.metadata for record in _risk_events(audit_log_repository)])
    assert serialized == '[{"risk_kind": "diabetes"}]'
    assert str(body.get("score", "")) not in serialized
    assert str(body.get("probability", "")) not in serialized
    if body.get("risk_level"):
        assert body["risk_level"] not in serialized


@pytest.mark.asyncio
async def test_cross_owner_risk_assessment_writes_failure_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    owner_headers = await register_and_login(client, email="ra-audit-owner@example.com")
    other_headers = await register_and_login(client, email="ra-audit-other@example.com")
    patient_id = await create_patient(client, owner_headers)
    audit_log_repository.records.clear()

    url = DIABETES_URL.format(patient_id=patient_id, date_range=ASSESSMENT_DATE_RANGE)
    response = await client.get(url, headers=other_headers)
    assert response.status_code == 404

    events = _risk_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].outcome == AuditOutcome.FAILURE
    assert events[0].http_status == 404
    assert events[0].resource_id == UUID(patient_id)
    assert events[0].metadata == {"risk_kind": "diabetes"}


@pytest.mark.asyncio
async def test_risk_assessment_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await register_and_login(client, email="ra-audit-dup@example.com")
    patient_id = await create_patient(client, headers)
    audit_log_repository.records.clear()

    url = STROKE_URL.format(patient_id=patient_id, date_range=ASSESSMENT_DATE_RANGE)
    response = await client.get(url, headers=headers)
    assert response.status_code == 200
    assert len(_risk_events(audit_log_repository)) == 1


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_risk_response(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_append(record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(audit_log_repository, "append", failing_append)

    headers = await register_and_login(client, email=f"ra-fail-open-{uuid4().hex[:8]}@example.com")
    patient_id = await create_patient(client, headers)
    url = HEART_URL.format(patient_id=patient_id, date_range=ASSESSMENT_DATE_RANGE)

    response = await client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["patient_id"] == patient_id
