"""Unit tests for ClinicalEncounterService (in-memory repository + policy)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.clinical_decision.time_ports import ClockPort
from app.application.clinical_encounter.exceptions import (
    ActiveClinicalEncounterAlreadyExists,
    ClinicalEncounterAccessDeniedError,
    ClinicalEncounterNotFoundError,
    ClinicalEncounterOwnershipError,
    ClinicalEncounterStaleVersionError,
)
from app.application.services.clinical_encounter_service import ClinicalEncounterService
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import EncounterStatus, FindingType, QuestionAnswerType
from app.domain.clinical_encounter.exceptions import (
    EncounterAlreadyFinalizedError,
    EncounterCancelledError,
    InvalidEncounterFinalSummaryError,
)
from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentStatus, ConsentType
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.clinical_encounter.exceptions import ClinicalEncounterConcurrencyError
from tests.support.clinical_encounter_service_factory import build_clinical_encounter_service
from tests.support.memory_application_transaction import TrackingApplicationTransaction
from tests.support.memory_clinical_encounter_repository import InMemoryClinicalEncounterRepository
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_consent_repository import InMemoryPatientConsentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository


class FixedClock(ClockPort):
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now_utc(self) -> datetime:
        return self._moment


_T0 = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


async def _seed_org_patient(
    *,
    doctor_a,
    doctor_b=None,
    assign_b: bool = False,
):
    org_id = uuid4()
    patient_id = uuid4()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)
    memberships = InMemoryOrganizationMembershipRepository()

    await memberships.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=doctor_a,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    if doctor_b is not None:
        await memberships.create(
            OrganizationMembership(
                organization_id=org_id,
                user_id=doctor_b,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )

    await patients.create(
        Patient(
            id=patient_id,
            owner_id=doctor_a,
            organization_id=org_id,
            first_name="Enc",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            gender="female",
        ),
    )
    await assignments.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient_id,
            assignee_user_id=doctor_a,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    if doctor_b is not None and assign_b:
        await assignments.create(
            PatientAssignment(
                organization_id=org_id,
                patient_id=patient_id,
                assignee_user_id=doctor_b,
                is_primary=False,
                status=AssignmentStatus.ACTIVE,
            ),
        )
    return patients, memberships, assignments, org_id, patient_id, doctor_a


def _service(
    patients,
    memberships,
    assignments,
    encounters=None,
    *,
    settings=None,
    consent=None,
    transaction=None,
    clock=None,
    audit_hook=None,
) -> ClinicalEncounterService:
    svc = build_clinical_encounter_service(
        encounter_repository=encounters or InMemoryClinicalEncounterRepository(),
        patient_repository=patients,
        membership_repository=memberships,
        assignment_repository=assignments,
        settings=settings,
        consent_repository=consent,
        transaction=transaction,
        audit_hook=audit_hook,
    )
    if clock is not None:
        svc._clock = clock  # noqa: SLF001 — test seam
    return svc


@pytest.mark.asyncio
async def test_assigned_doctor_can_create_active_encounter() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    created = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
        locale="tr",
    )
    assert created.encounter.status == EncounterStatus.ACTIVE
    assert created.encounter.clinician_user_id == doctor_a
    assert created.encounter.started_at == _T0


@pytest.mark.asyncio
async def test_unassigned_doctor_cannot_create() -> None:
    doctor_a = uuid4()
    doctor_b = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
        doctor_b=doctor_b,
    )
    service = _service(patients, memberships, assignments)

    with pytest.raises(NotFoundError):
        await service.create_encounter(
            doctor_b,
            UserRole.DOCTOR,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )


@pytest.mark.asyncio
async def test_second_active_encounter_rejected() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    encounters = InMemoryClinicalEncounterRepository()
    service = _service(patients, memberships, assignments, encounters=encounters, clock=FixedClock(_T0))

    await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    with pytest.raises(ActiveClinicalEncounterAlreadyExists):
        await service.create_encounter(
            doctor_a,
            UserRole.DOCTOR,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )


@pytest.mark.asyncio
async def test_starter_can_add_complaint_and_finding_and_response() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    with_complaint = await service.add_complaint(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
    )
    assert len(with_complaint.complaints) == 1

    with_finding = await service.add_finding(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        finding_type=FindingType.SYMPTOM,
        finding_key="copilot.test.finding",
    )
    assert len(with_finding.findings) == 1

    with_response = await service.record_question_response(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="yes",
    )
    assert len(with_response.question_responses) == 1


@pytest.mark.asyncio
async def test_other_assigned_doctor_cannot_mutate() -> None:
    doctor_a = uuid4()
    doctor_b = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
        doctor_b=doctor_b,
        assign_b=True,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    with pytest.raises(ClinicalEncounterOwnershipError):
        await service.add_complaint(
            doctor_b,
            UserRole.DOCTOR,
            enc.encounter.id,
            complaint_key="copilot.test.complaint",
        )


@pytest.mark.asyncio
async def test_question_response_soft_deactivates_previous() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    encounters = InMemoryClinicalEncounterRepository()
    service = _service(patients, memberships, assignments, encounters=encounters, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    first = await service.record_question_response(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="yes",
    )
    assert len(first.question_responses) == 1
    second = await service.record_question_response(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="no",
    )
    assert len(second.question_responses) == 1
    assert second.question_responses[0].answer_code == "no"
    stored = encounters._aggregates[enc.encounter.id]  # noqa: SLF001
    historical = [r for r in stored.question_responses if not r.is_active]
    assert len(historical) == 1
    assert historical[0].answer_code == "yes"


@pytest.mark.asyncio
async def test_finalized_encounter_cannot_mutate() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    finalized = await service.finalize_encounter(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
    )
    assert finalized.encounter.status == EncounterStatus.FINALIZED
    assert finalized.final_summary is not None
    with pytest.raises(EncounterAlreadyFinalizedError):
        await service.add_complaint(
            doctor_a,
            UserRole.DOCTOR,
            enc.encounter.id,
            complaint_key="copilot.test.complaint",
        )


@pytest.mark.asyncio
async def test_cancel_encounter_terminal() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    cancelled = await service.cancel_encounter(doctor_a, UserRole.DOCTOR, enc.encounter.id)
    assert cancelled.encounter.status == EncounterStatus.CANCELLED
    assert cancelled.final_summary is None


@pytest.mark.asyncio
async def test_access_failure_does_not_persist_encounter() -> None:
    doctor_a = uuid4()
    doctor_b = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
        doctor_b=doctor_b,
    )
    encounters = InMemoryClinicalEncounterRepository()
    txn = TrackingApplicationTransaction()
    service = _service(
        patients,
        memberships,
        assignments,
        encounters=encounters,
        transaction=txn,
        clock=FixedClock(_T0),
    )

    with pytest.raises(NotFoundError):
        await service.create_encounter(
            doctor_b,
            UserRole.DOCTOR,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )
    assert encounters._aggregates == {}  # noqa: SLF001
    assert txn.committed is False


@pytest.mark.asyncio
async def test_consent_failure_does_not_persist_encounter() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    encounters = InMemoryClinicalEncounterRepository()
    consent = InMemoryPatientConsentRepository()
    settings = Settings(clinical_consent_enforced=True)
    txn = TrackingApplicationTransaction()
    service = _service(
        patients,
        memberships,
        assignments,
        encounters=encounters,
        settings=settings,
        consent=consent,
        transaction=txn,
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
    assert encounters._aggregates == {}  # noqa: SLF001
    assert txn.committed is False


@pytest.mark.asyncio
async def test_consent_granted_allows_create() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    consent = InMemoryPatientConsentRepository()
    await consent.create(
        PatientConsent(
            patient_id=patient_id,
            organization_id=org_id,
            consent_type=ConsentType.CLINICAL_DATA_PROCESSING,
            status=ConsentStatus.GRANTED,
            version=1,
            granted_at=_T0,
            recorded_by_user_id=doctor_a,
        ),
    )
    settings = Settings(clinical_consent_enforced=True)
    service = _service(
        patients,
        memberships,
        assignments,
        settings=settings,
        consent=consent,
        clock=FixedClock(_T0),
    )
    created = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    assert created.encounter.status == EncounterStatus.ACTIVE


@pytest.mark.asyncio
async def test_stale_version_surfaces_conflict() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    encounters = InMemoryClinicalEncounterRepository()
    service = _service(patients, memberships, assignments, encounters=encounters, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    stale = await encounters.get_by_id(enc.encounter.id)
    assert stale is not None
    await service.add_complaint(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
    )

    async def failing_save(_aggregate):
        raise ClinicalEncounterConcurrencyError("stale")

    original_save = encounters.save
    encounters.save = failing_save  # type: ignore[method-assign]
    try:
        with pytest.raises(ClinicalEncounterStaleVersionError):
            await service.add_complaint(
                doctor_a,
                UserRole.DOCTOR,
                enc.encounter.id,
                complaint_key="copilot.test.other",
            )
    finally:
        encounters.save = original_save  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_list_and_read_follow_access_rules() -> None:
    doctor_a = uuid4()
    doctor_b = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
        doctor_b=doctor_b,
        assign_b=True,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    listed = await service.list_patient_encounters(
        doctor_b,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
    )
    assert len(listed) == 1
    loaded = await service.get_encounter(doctor_b, UserRole.DOCTOR, enc.encounter.id)
    assert loaded.encounter.id == enc.encounter.id


@pytest.mark.asyncio
async def test_clinic_admin_cannot_mutate_encounter() -> None:
    doctor_a = uuid4()
    admin = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    await memberships.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=admin,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))

    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    with pytest.raises(ClinicalEncounterAccessDeniedError):
        await service.add_complaint(
            admin,
            UserRole.CLINIC_ADMIN,
            enc.encounter.id,
            complaint_key="copilot.test.complaint",
        )


@pytest.mark.asyncio
async def test_system_admin_cannot_create_encounter() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))
    admin = uuid4()

    with pytest.raises(ForbiddenError):
        await service.create_encounter(
            admin,
            UserRole.SYSTEM_ADMIN,
            patient_id=patient_id,
            organization_id=org_id,
            specialty_key="cardiology",
        )


@pytest.mark.asyncio
async def test_finalize_commits_via_transaction() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    txn = TrackingApplicationTransaction()
    service = _service(
        patients,
        memberships,
        assignments,
        transaction=txn,
        clock=FixedClock(_T0),
    )
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    await service.finalize_encounter(
        doctor_a,
        UserRole.DOCTOR,
        enc.encounter.id,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
    )
    assert txn.committed is True


@pytest.mark.asyncio
async def test_finalize_invalid_summary_rolls_back_transaction() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    txn = TrackingApplicationTransaction()
    service = _service(
        patients,
        memberships,
        assignments,
        transaction=txn,
        clock=FixedClock(_T0),
    )
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    with pytest.raises(InvalidEncounterFinalSummaryError):
        await service.finalize_encounter(
            doctor_a,
            UserRole.DOCTOR,
            enc.encounter.id,
            summary_sections=(),
        )
    assert txn.rolled_back is True
    reloaded = await service.get_encounter(doctor_a, UserRole.DOCTOR, enc.encounter.id)
    assert reloaded.encounter.status == EncounterStatus.ACTIVE


@pytest.mark.asyncio
async def test_cancelled_encounter_immutable() -> None:
    doctor_a = uuid4()
    patients, memberships, assignments, org_id, patient_id, _ = await _seed_org_patient(
        doctor_a=doctor_a,
    )
    service = _service(patients, memberships, assignments, clock=FixedClock(_T0))
    enc = await service.create_encounter(
        doctor_a,
        UserRole.DOCTOR,
        patient_id=patient_id,
        organization_id=org_id,
        specialty_key="cardiology",
    )
    await service.cancel_encounter(doctor_a, UserRole.DOCTOR, enc.encounter.id)
    with pytest.raises(EncounterCancelledError):
        await service.add_finding(
            doctor_a,
            UserRole.DOCTOR,
            enc.encounter.id,
            finding_type=FindingType.SYMPTOM,
            finding_key="copilot.test.finding",
        )
