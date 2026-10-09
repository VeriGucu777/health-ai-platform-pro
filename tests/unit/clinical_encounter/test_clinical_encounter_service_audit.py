"""ClinicalEncounterService audit integration (in-memory hook)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.application.clinical_encounter.exceptions import ClinicalEncounterOwnershipError
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.config import Settings
from app.domain.clinical_encounter.entities import EncounterSummarySection
from app.domain.clinical_encounter.enums import FindingType, QuestionAnswerType
from app.domain.entities.user import UserRole
from tests.support.clinical_encounter_service_factory import build_clinical_encounter_service
from tests.support.memory_application_transaction import TrackingApplicationTransaction
from tests.support.memory_clinical_encounter_audit_hook import (
    FailingClinicalEncounterAuditHook,
    MemoryClinicalEncounterAuditHook,
)
from tests.support.memory_clinical_encounter_repository import InMemoryClinicalEncounterRepository
from tests.support.memory_patient_consent_repository import InMemoryPatientConsentRepository
from tests.unit.clinical_encounter.test_clinical_encounter_service import (
    FixedClock,
    _T0,
    _seed_org_patient,
    _service,
)

_PHI_MARKERS = (
    "clinician_display_text",
    "clinician_note",
    "copilot.test.complaint",
    "summary_sections",
)


@pytest.mark.asyncio
async def test_create_emits_one_create_audit_event() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    patients, memberships, assignments, org_id, patient_id, doctor_a = await _seed_org_patient(
        doctor_a=uuid4(),
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    assert len(audit.events) == 1
    assert audit.events[0].operation == "encounter_created"


@pytest.mark.asyncio
async def test_get_emits_view_audit() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    patients, memberships, assignments, org_id, patient_id, doctor_a = await _seed_org_patient(
        doctor_a=uuid4(),
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    created = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    audit.clear()
    await service.get_encounter(doctor_a, UserRole.DOCTOR, created.encounter.id)
    assert len(audit.events) == 1
    assert audit.events[0].operation == "encounter_viewed"


@pytest.mark.asyncio
async def test_list_emits_single_list_audit_not_per_row() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    patients, memberships, assignments, org_id, patient_id, doctor_a = await _seed_org_patient(
        doctor_a=uuid4(),
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    audit.clear()
    await service.list_patient_encounters(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
    )
    assert len(audit.events) == 1
    assert audit.events[0].operation == "encounter_list_viewed"
    assert audit.events[0].result_count == 1


@pytest.mark.asyncio
async def test_complaint_finding_response_finalize_cancel_audit() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    patients, memberships, assignments, org_id, patient_id, doctor_a = await _seed_org_patient(
        doctor_a=uuid4(),
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    audit.clear()
    await service.add_complaint(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
    )
    await service.add_finding(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        finding_type=FindingType.SYMPTOM,
        finding_key="copilot.test.finding",
    )
    await service.record_question_response(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="yes",
    )
    await service.record_question_response(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="no",
    )
    ops = [e.operation for e in audit.events]
    assert "complaint_added" in ops
    assert "finding_added" in ops
    assert "question_response_recorded" in ops
    assert "question_response_updated" in ops

    audit.clear()
    await service.finalize_encounter(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
        clinician_note="secret note must not appear in audit",
    )
    assert len(audit.events) == 1
    assert audit.events[0].operation == "encounter_finalized"
    assert audit.events[0].child_kind == "final_summary"

    audit.clear()
    enc2 = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    await service.cancel_encounter(doctor_a, UserRole.DOCTOR, enc2.encounter.id)
    assert audit.events[-1].operation == "encounter_cancelled"


@pytest.mark.asyncio
async def test_non_owner_mutation_emits_no_audit() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    doctor_a = uuid4()
    doctor_b = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
        doctor_b=doctor_b,
        assign_b=True,
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    audit.clear()
    with pytest.raises(ClinicalEncounterOwnershipError):
        await service.add_complaint(
            doctor_b,
            UserRole.DOCTOR,
            enc.encounter.id,
            complaint_key="copilot.test.complaint",
        )
    assert audit.events == []


@pytest.mark.asyncio
async def test_consent_failure_no_mutation_audit() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        settings=Settings(clinical_consent_enforced=True),
        consent=InMemoryPatientConsentRepository(),
        clock=FixedClock(_T0),
    )
    with pytest.raises(ForbiddenError):
        await service.create_encounter(
            doctor_a,
            UserRole.DOCTOR,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )
    assert audit.events == []


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_mutation_transaction() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    encounters = InMemoryClinicalEncounterRepository()
    txn = TrackingApplicationTransaction()
    service = _service(
        patients,
        memberships,
        assignments,
        encounters=encounters,
        transaction=txn,
        audit_hook=FailingClinicalEncounterAuditHook(),
        clock=FixedClock(_T0),
    )
    with pytest.raises(RuntimeError):
        await service.create_encounter(
            doctor_a,
            UserRole.DOCTOR,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )
    assert txn.rolled_back is True


@pytest.mark.asyncio
async def test_audit_metadata_has_no_phi_fixture_strings() -> None:
    audit = MemoryClinicalEncounterAuditHook()
    patients, memberships, assignments, org_id, patient_id, doctor_a = await _seed_org_patient(
        doctor_a=uuid4(),
    )
    service = _service(
        patients,
        memberships,
        assignments,
        audit_hook=audit,
        clock=FixedClock(_T0),
    )
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    await service.add_complaint(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
        clinician_display_text="PHI display text",
    )
    blob = json.dumps(
        [
            {
                "operation": e.operation,
                "child_kind": e.child_kind,
                "child_id": str(e.child_id) if e.child_id else None,
                "specialty_key": e.specialty_key,
            }
            for e in audit.events
        ],
    )
    for marker in _PHI_MARKERS:
        assert marker not in blob
