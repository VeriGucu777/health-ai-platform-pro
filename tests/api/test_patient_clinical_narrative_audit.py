"""Clinical narrative audit tests."""

import json

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from tests.api.test_patient_clinical_narrative import NARRATIVE_URL, PATIENT_PAYLOAD, _register_and_login
from tests.support.clinical_api_test_helpers import assigned_patient_for_doctor


def _events(repo):
    return [r for r in repo.list_all() if r.resource_type == AuditResourceType.CLINICAL_NARRATIVE]


@pytest.mark.asyncio
async def test_narrative_success_audit_phi_safe(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    headers = await _register_and_login(client, email="narr-audit@example.com")
    patient_id = await assigned_patient_for_doctor(
        client,
        user_repository,
        membership_repository,
        headers,
        patient_payload=PATIENT_PAYLOAD,
    )
    audit_log_repository.records.clear()
    response = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={"query": "secret patient diagnosis keyword"},
    )
    assert response.status_code == 200
    events = _events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.GENERATE
    assert events[0].outcome == AuditOutcome.SUCCESS
    meta = events[0].metadata or {}
    blob = json.dumps(meta).lower()
    assert "secret" not in blob
    assert "diagnosis" not in blob
    assert "query" not in blob
    assert meta.get("narrative_version") == "llm_clinical_narrative_v1"
    assert meta.get("prompt_version") == "clinical_narrative_prompt_v1"
