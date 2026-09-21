"""Health summary PDF export audit integration tests."""

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from tests.api.test_patient_health_reports import REPORT_DATE_RANGE, _create_patient, _register_and_login
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def _report_url(patient_id: str, *, date_range: str = REPORT_DATE_RANGE) -> str:
    return f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{date_range}"


def _health_report_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [
        record
        for record in repo.list_all()
        if record.resource_type == AuditResourceType.HEALTH_REPORT
    ]


@pytest.mark.asyncio
async def test_pdf_export_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="phr-audit-ok@example.com")
    patient_id = await _create_patient(client, headers)
    audit_log_repository.records.clear()

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

    events = _health_report_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.EXPORT
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.resource_id == UUID(patient_id)
    assert event.http_status == 200
    assert event.metadata == {"report": "health_summary", "format": "pdf"}


@pytest.mark.asyncio
async def test_pdf_audit_metadata_excludes_phi_and_pdf_bytes(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(
        client,
        email="phr-audit-phi@example.com",
        first_name="Sensitive",
        last_name="PatientName",
    )
    patient_id = await _create_patient(
        client,
        headers,
        first_name="HiddenFirst",
        last_name="HiddenLast",
    )
    audit_log_repository.records.clear()

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert b"HiddenFirst" in response.content or len(response.content) > 100

    metadata = _health_report_events(audit_log_repository)[0].metadata
    assert metadata == {"report": "health_summary", "format": "pdf"}
    serialized = json.dumps(metadata)
    assert "HiddenFirst" not in serialized
    assert "HiddenLast" not in serialized
    assert "%PDF" not in serialized


@pytest.mark.asyncio
async def test_cross_owner_pdf_export_writes_failure_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    owner_headers = await _register_and_login(client, email="phr-audit-owner@example.com")
    other_headers = await _register_and_login(client, email="phr-audit-other@example.com")
    patient_id = await _create_patient(client, owner_headers)
    audit_log_repository.records.clear()

    response = await client.get(_report_url(patient_id), headers=other_headers)
    assert response.status_code == 404

    events = _health_report_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].outcome == AuditOutcome.FAILURE
    assert events[0].http_status == 404
    assert events[0].resource_id == UUID(patient_id)
    assert events[0].metadata == {"report": "health_summary", "format": "pdf"}


@pytest.mark.asyncio
async def test_pdf_export_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="phr-audit-dup@example.com")
    patient_id = await _create_patient(client, headers)
    audit_log_repository.records.clear()

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert len(_health_report_events(audit_log_repository)) == 1


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_pdf_response(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_append(record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(audit_log_repository, "append", failing_append)

    headers = await _register_and_login(
        client,
        email=f"phr-fail-open-{uuid4().hex[:8]}@example.com",
    )
    patient_id = await _create_patient(client, headers)

    response = await client.get(_report_url(patient_id), headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
