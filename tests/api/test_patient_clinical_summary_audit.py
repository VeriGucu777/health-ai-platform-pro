"""Clinical summary audit integration tests."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.application.clinical_summary.constants import SUMMARY_VERSION
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from tests.api.test_patient_clinical_summary import PATIENT_PAYLOAD, _register_and_login
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def _summary_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [
        record
        for record in repo.list_all()
        if record.resource_type == AuditResourceType.PATIENT_CLINICAL_SUMMARY
    ]


@pytest.mark.asyncio
async def test_summary_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="sum-audit-ok@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-summary",
        headers=headers,
    )
    assert response.status_code == 200

    events = _summary_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.VIEW
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == patient_id
    assert event.http_status == 200


@pytest.mark.asyncio
async def test_summary_audit_metadata_phi_safe(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="sum-audit-meta@example.com")
    patient_id = UUID(
        (
            await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
        ).json()["id"]
    )
    record_date = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    await client.post(
        "/api/v1/medical-records",
        json={
            "patient_id": str(patient_id),
            "record_date": record_date,
            "record_type": "visit",
            "title": "Secret diagnosis visit",
            "diagnosis": "Sensitive diagnosis",
            "medications": "SecretMed",
        },
        headers=headers,
    )
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-summary"
        "?date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z",
        headers=headers,
    )
    assert response.status_code == 200

    metadata = _summary_events(audit_log_repository)[0].metadata
    assert metadata is not None
    assert metadata["summary_version"] == SUMMARY_VERSION
    assert "date_from" in metadata
    assert "date_to" in metadata
    blob = json.dumps(metadata).lower()
    assert "diagnosis" not in blob
    assert "secretmed" not in blob
    assert "score" not in blob
    assert "probability" not in blob


@pytest.mark.asyncio
async def test_summary_failure_audit_enumeration_safe(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="sum-audit-fail@example.com")
    audit_log_repository.records.clear()
    missing_id = "00000000-0000-4000-8000-000000000077"

    response = await client.get(
        f"/api/v1/patients/{missing_id}/clinical-summary",
        headers=headers,
    )
    assert response.status_code == 404

    events = _summary_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].outcome == AuditOutcome.FAILURE
    assert events[0].http_status == 404
