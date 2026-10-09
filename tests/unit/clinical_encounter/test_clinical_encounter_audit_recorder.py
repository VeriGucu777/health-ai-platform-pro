"""Clinical encounter audit recorder and metadata safety tests."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.application.clinical_encounter.audit_events import ClinicalEncounterAuditEvent
from app.application.dtos.audit_log import AuditRecordInput
from app.application.services.audit_service import AuditService
from app.application.services.clinical_encounter_audit_recorder import ClinicalEncounterAuditRecorder
from app.core.exceptions import ValidationError
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.user import UserRole
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository

_PHI_MARKERS = (
    "clinician_display_text",
    "clinician_note",
    "copilot.test.complaint",
    "summary_sections",
    "answer_code",
)


@pytest.mark.asyncio
async def test_recorder_persists_clinical_encounter_create() -> None:
    repo = InMemoryAuditLogRepository()
    recorder = ClinicalEncounterAuditRecorder(AuditService(repo))
    actor = uuid4()
    patient = uuid4()
    org = uuid4()
    encounter = uuid4()

    await recorder.record_event(
        ClinicalEncounterAuditEvent(
            operation="encounter_created",
            actor_id=actor,
            actor_role=UserRole.DOCTOR,
            organization_id=org,
            patient_id=patient,
            encounter_id=encounter,
            encounter_version=2,
            encounter_status="active",
            specialty_key="cardiology",
        ),
    )

    assert len(repo.list_all()) == 1
    row = repo.list_all()[0]
    assert row.resource_type == AuditResourceType.CLINICAL_ENCOUNTER
    assert row.action == AuditAction.CREATE
    assert row.resource_id == encounter
    assert row.metadata is not None
    assert row.metadata["operation"] == "encounter_created"
    serialized = json.dumps(row.metadata)
    for marker in _PHI_MARKERS:
        assert marker not in serialized


@pytest.mark.asyncio
async def test_recorder_rejects_forbidden_metadata_via_sanitize() -> None:
    repo = InMemoryAuditLogRepository()
    service = AuditService(repo)

    with pytest.raises(ValidationError):
        await service.record(
            AuditRecordInput(
                resource_type=AuditResourceType.CLINICAL_ENCOUNTER,
                action=AuditAction.UPDATE,
                outcome=AuditOutcome.SUCCESS,
                metadata={"diagnosis": "secret"},
            ),
        )
