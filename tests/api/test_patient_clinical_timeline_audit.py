"""Clinical timeline audit integration tests."""

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from tests.api.test_patient_clinical_timeline import PATIENT_PAYLOAD, _register_and_login
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def _timeline_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [
        record
        for record in repo.list_all()
        if record.resource_type == AuditResourceType.PATIENT_CLINICAL_TIMELINE
    ]


@pytest.mark.asyncio
async def test_timeline_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="tl-audit-ok@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200

    events = _timeline_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.VIEW
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == patient_id
    assert event.http_status == 200


@pytest.mark.asyncio
async def test_timeline_audit_metadata_fields(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="tl-audit-meta@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline"
        "?date_from=2026-01-01T00:00:00Z"
        "&date_to=2026-02-01T00:00:00Z"
        "&include_risk_snapshot=true"
        "&max_events=50",
        headers=headers,
    )
    assert response.status_code == 200

    metadata = _timeline_events(audit_log_repository)[0].metadata
    assert metadata is not None
    assert metadata["date_from"] == "2026-01-01T00:00:00+00:00"
    assert metadata["date_to"] == "2026-02-01T00:00:00+00:00"
    assert metadata["include_risk_snapshot"] is True
    assert "max_events" not in metadata


@pytest.mark.asyncio
async def test_timeline_audit_contains_no_phi_from_response(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    from datetime import UTC, datetime, timedelta

    headers = await _register_and_login(client, email="tl-audit-phi@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    record_date = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": str(patient_id),
            "record_date": record_date,
            "record_type": "visit",
            "title": "Secret visit",
            "diagnosis": "SensitiveDiagnosisXYZ",
        },
        headers=headers,
    )
    audit_log_repository.records.clear()

    timeline_response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert timeline_response.status_code == 200
    assert "SensitiveDiagnosisXYZ" in timeline_response.text

    serialized = json.dumps(
        [record.metadata for record in _timeline_events(audit_log_repository)],
        default=str,
    )
    assert "SensitiveDiagnosisXYZ" not in serialized
    assert "Jane" not in serialized
    assert "Timeline" not in serialized


@pytest.mark.asyncio
async def test_cross_owner_timeline_writes_failure_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    owner_headers = await _register_and_login(client, email="tl-audit-owner@example.com")
    other_headers = await _register_and_login(client, email="tl-audit-other@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=owner_headers)
        ).json()["id"]
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=other_headers,
    )
    assert response.status_code == 404

    events = _timeline_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].outcome == AuditOutcome.FAILURE
    assert events[0].resource_id == patient_id
    assert events[0].http_status == 404


@pytest.mark.asyncio
async def test_timeline_view_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="tl-audit-dup@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    assert len(_timeline_events(audit_log_repository)) == 1


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_timeline_response(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_append(record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(audit_log_repository, "append", failing_append)

    headers = await _register_and_login(
        client,
        email=f"tl-fail-open-{uuid4().hex[:8]}@example.com",
    )
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["patient_id"] == str(patient_id)
