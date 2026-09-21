"""Patient CRUD audit integration tests."""

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from tests.api.test_patients import PATIENT_PAYLOAD, _register_and_login
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def _patient_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [
        record for record in repo.list_all() if record.resource_type == AuditResourceType.PATIENT
    ]


@pytest.mark.asyncio
async def test_patient_list_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-list@example.com")
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.LIST
    assert events[0].outcome == AuditOutcome.SUCCESS
    assert events[0].resource_id is None
    assert events[0].metadata == {"page": 1, "page_size": 20}


@pytest.mark.asyncio
async def test_patient_view_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-view@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = UUID(created.json()["id"])
    audit_log_repository.records.clear()

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 200

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.VIEW
    assert events[0].resource_id == patient_id


@pytest.mark.asyncio
async def test_patient_create_success_audits_new_resource_id(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-create@example.com")
    audit_log_repository.records.clear()

    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    patient_id = UUID(response.json()["id"])

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.CREATE
    assert events[0].resource_id == patient_id


@pytest.mark.asyncio
async def test_patient_update_success_writes_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-update@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = UUID(created.json()["id"])
    audit_log_repository.records.clear()

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"first_name": "Updated"},
        headers=headers,
    )
    assert response.status_code == 200

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.UPDATE
    assert events[0].resource_id == patient_id


@pytest.mark.asyncio
async def test_patient_delete_success_writes_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-delete@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = UUID(created.json()["id"])
    audit_log_repository.records.clear()

    response = await client.delete(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 204

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.DELETE
    assert events[0].resource_id == patient_id


@pytest.mark.asyncio
async def test_cross_owner_get_writes_failure_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    owner_headers = await _register_and_login(client, email="pa-owner@example.com")
    other_headers = await _register_and_login(client, email="pa-other@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=owner_headers)
    patient_id = UUID(created.json()["id"])
    audit_log_repository.records.clear()

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=other_headers)
    assert response.status_code == 404

    events = _patient_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.VIEW
    assert events[0].outcome == AuditOutcome.FAILURE
    assert events[0].resource_id == patient_id
    assert events[0].http_status == 404


@pytest.mark.asyncio
async def test_patient_audit_metadata_contains_no_phi(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    payload = {
        **PATIENT_PAYLOAD,
        "first_name": "SensitiveFirst",
        "last_name": "SensitiveLast",
        "phone": "+15559998888",
        "notes": "Secret clinical note",
    }
    headers = await _register_and_login(client, email="pa-phi@example.com")
    audit_log_repository.records.clear()

    await client.post("/api/v1/patients", json=payload, headers=headers)

    serialized = json.dumps(
        [record.metadata for record in _patient_events(audit_log_repository)],
        default=str,
    )
    assert "SensitiveFirst" not in serialized
    assert "SensitiveLast" not in serialized
    assert "+15559998888" not in serialized
    assert "Secret clinical note" not in serialized


@pytest.mark.asyncio
async def test_patient_view_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="pa-dup@example.com")
    created = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    patient_id = UUID(created.json()["id"])
    audit_log_repository.records.clear()

    response = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 200
    assert len(_patient_events(audit_log_repository)) == 1


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_patient_create(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_append(record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(audit_log_repository, "append", failing_append)

    headers = await _register_and_login(
        client,
        email=f"pa-fail-open-{uuid4().hex[:8]}@example.com",
    )
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
