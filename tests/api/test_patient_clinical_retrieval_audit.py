"""Clinical retrieval audit tests."""

import json

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from tests.api.test_patient_clinical_retrieval import PATIENT_PAYLOAD, _register_and_login
from tests.support.clinical_api_test_helpers import assigned_patient_for_doctor
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def _events(repo: InMemoryAuditLogRepository):
    return [r for r in repo.list_all() if r.resource_type == AuditResourceType.CLINICAL_RETRIEVAL]


@pytest.mark.asyncio
async def test_retrieval_success_audit_phi_safe(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="retr-audit@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    audit_log_repository.records.clear()
    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-retrieval",
        headers=headers,
        json={"query": "secret diagnosis keyword", "top_k": 2},
    )
    assert response.status_code == 200
    events = _events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.SEARCH
    meta = events[0].metadata or {}
    blob = json.dumps(meta).lower()
    assert "secret" not in blob
    assert "diagnosis" not in blob
    assert meta.get("retrieval_version") == "rag_retrieval_v1"
    assert meta.get("top_k") == 2
