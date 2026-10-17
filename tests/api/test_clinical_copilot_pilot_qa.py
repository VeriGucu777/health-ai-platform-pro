"""Pilot QA — end-to-end hypertension Clinical Copilot technical flow (synthetic data)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.clinical_decision.enums import EvaluationStatus
from app.infrastructure.clinical_knowledge.validated_catalog_provider import (
    ValidatedFilesystemClinicalRuleCatalogProvider,
)
from tests.support.hypertension_copilot_pilot_scenario import build_hypertension_pilot_qa_context


def _copilot_audit_rows(audit_log_repository) -> list:
    return [
        row
        for row in audit_log_repository.list_all()
        if row.resource_type == AuditResourceType.CLINICAL_ENCOUNTER
        and row.metadata
        and str(row.metadata.get("operation", "")).startswith("copilot_evaluation_")
    ]


_FORBIDDEN_RESPONSE_KEYS = frozenset(
    {
        "differential_candidates",
        "treatment_recommendations",
        "medication_recommendations",
        "safety_alerts",
        "hypertension_stage",
        "diagnosis",
    },
)


@pytest.mark.asyncio
async def test_pilot_qa_synthetic_flow_evaluate_empty_safe_with_provenance_and_audit(
    client: AsyncClient,
    user_repository,
    membership_repository,
    audit_log_repository,
) -> None:
    catalog = ValidatedFilesystemClinicalRuleCatalogProvider.load()
    assert catalog.rule_catalog.list_active_production_rules("cardiology") == ()

    ctx = await build_hypertension_pilot_qa_context(
        client,
        user_repository,
        membership_repository,
    )
    headers = ctx["headers"]
    patient_id = str(ctx["patient_id"])
    encounter_id = str(ctx["encounter_id"])
    assert ctx["encounter_detail"]["encounter"]["status"] == "active"
    assert ctx["encounter_detail"]["encounter"]["specialty_key"] == "cardiology"

    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters/{encounter_id}/evaluate",
        headers=headers,
        json={"context_profile": "hypertension_v1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["evaluation_status"] == EvaluationStatus.NO_APPLICABLE_RULES.value
    assert body["missing_information"] == []
    assert body["review_domain_status"] == []
    assert body["documentation_reminders"] == []
    assert body["read_only"] is False

    for key in _FORBIDDEN_RESPONSE_KEYS:
        assert key not in body

    assert "differential" not in body
    assert "treatment" not in response.text.lower()

    prov = body["provenance"]
    assert prov["context_profile"] == "hypertension_v1"
    assert prov["input_snapshot_id"]
    assert prov["specialty_key"] == "cardiology"
    assert prov["engine_version"]
    assert prov["rule_provenance"] == []

    audits = _copilot_audit_rows(audit_log_repository)
    ops = {row.metadata.get("operation") for row in audits}
    assert "copilot_evaluation_requested" in ops
    assert "copilot_evaluation_succeeded" in ops
    succeeded = next(r for r in audits if r.metadata.get("operation") == "copilot_evaluation_succeeded")
    assert succeeded.action == AuditAction.EXECUTE
    assert succeeded.outcome == AuditOutcome.SUCCESS
    assert succeeded.metadata.get("context_profile") == "hypertension_v1"
    assert succeeded.metadata.get("input_snapshot_id")
