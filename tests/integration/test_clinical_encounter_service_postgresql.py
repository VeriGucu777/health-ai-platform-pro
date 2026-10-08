"""PostgreSQL integration tests for ClinicalEncounterService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.clinical_decision.time_ports import ClockPort
from app.application.clinical_encounter.exceptions import (
    ActiveClinicalEncounterAlreadyExists,
    ClinicalEncounterOwnershipError,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.clinical_encounter.exceptions import ClinicalEncounterConcurrencyError
from app.application.services.clinical_encounter_service import ClinicalEncounterService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.domain.clinical_encounter.entities import EncounterSummarySection
from app.domain.clinical_encounter.enums import EncounterStatus, FindingType, QuestionAnswerType
from app.domain.entities.user import UserRole
from app.domain.organization.entities import Organization, OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.application_transaction import AsyncSessionApplicationTransaction
from app.infrastructure.repositories.clinical_encounter_repository import (
    SQLAlchemyClinicalEncounterRepository,
)
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.organization_repository import SQLAlchemyOrganizationRepository
from app.infrastructure.repositories.patient_assignment_repository import (
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_patient, make_user

_T0 = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)


class _FixedClock(ClockPort):
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now_utc(self) -> datetime:
        return self._moment


async def _seed_org_context(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
):
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)

    org = await org_repo.create(Organization(name="EncSvc Org", slug=f"enc-{uuid4().hex[:8]}"))
    doctor_a = await user_repository.create(make_user(role=UserRole.DOCTOR))
    doctor_b = await user_repository.create(make_user(role=UserRole.DOCTOR))
    await db_session.commit()

    patient = await patient_repository.create(
        make_patient(owner_id=doctor_a.id, organization_id=org.id),
    )
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=doctor_a.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=doctor_b.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repo.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=patient.id,
            assignee_user_id=doctor_a.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await assignment_repo.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=patient.id,
            assignee_user_id=doctor_b.id,
            is_primary=False,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await db_session.commit()
    return org, doctor_a, doctor_b, patient


def _service(db_session: AsyncSession) -> ClinicalEncounterService:
    patient_repo = SQLAlchemyPatientRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)
    policy = DefaultPatientAccessPolicy(patient_repo, membership_repo, assignment_repo)
    clock = _FixedClock(_T0)
    return ClinicalEncounterService(
        SQLAlchemyClinicalEncounterRepository(db_session),
        patient_repo,
        access_policy=policy,
        membership_repository=membership_repo,
        transaction=AsyncSessionApplicationTransaction(db_session),
        clock=clock,
    )


@pytest.mark.asyncio
async def test_create_encounter_commits_active_row(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, _, patient = await _seed_org_context(db_session, user_repository, patient_repository)
    service = _service(db_session)
    created = await service.create_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
        locale="tr",
    )
    assert created.encounter.status == EncounterStatus.ACTIVE
    reloaded = await service.get_encounter(doctor_a.id, UserRole.DOCTOR, created.encounter.id)
    assert reloaded.encounter.started_at == _T0


@pytest.mark.asyncio
async def test_second_active_encounter_maps_to_application_conflict(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, _, patient = await _seed_org_context(db_session, user_repository, patient_repository)
    service = _service(db_session)
    await service.create_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )
    with pytest.raises(ActiveClinicalEncounterAlreadyExists):
        await service.create_encounter(
            doctor_a.id,
            UserRole.DOCTOR,
            patient_id=patient.id,
            organization_id=org.id,
            specialty_key="cardiology",
        )


@pytest.mark.asyncio
async def test_child_mutations_and_finalize_persist(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, _, patient = await _seed_org_context(db_session, user_repository, patient_repository)
    service = _service(db_session)
    enc = await service.create_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )
    with_complaint = await service.add_complaint(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
    )
    assert with_complaint.complaints
    with_finding = await service.add_finding(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        finding_type=FindingType.SYMPTOM,
        finding_key="copilot.test.finding",
    )
    assert with_finding.findings
    with_response = await service.record_question_response(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="yes",
    )
    assert with_response.question_responses
    updated = await service.record_question_response(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        question_key="copilot.test.q",
        answer_type=QuestionAnswerType.BOOLEAN,
        answer_code="no",
    )
    assert updated.question_responses[0].answer_code == "no"

    finalized = await service.finalize_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
    )
    assert finalized.encounter.status == EncounterStatus.FINALIZED
    assert finalized.final_summary is not None


@pytest.mark.asyncio
async def test_non_owner_cannot_mutate(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, doctor_b, patient = await _seed_org_context(
        db_session,
        user_repository,
        patient_repository,
    )
    service = _service(db_session)
    enc = await service.create_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )
    with pytest.raises(ClinicalEncounterOwnershipError):
        await service.add_complaint(
            doctor_b.id,
            UserRole.DOCTOR,
            enc.encounter.id,
            complaint_key="copilot.test.complaint",
        )


@pytest.mark.asyncio
async def test_stale_concurrency_rejected_at_repository(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, _, patient = await _seed_org_context(db_session, user_repository, patient_repository)
    service = _service(db_session)
    enc = await service.create_encounter(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    stale = await repo.get_by_id(enc.encounter.id)
    assert stale is not None
    await service.add_complaint(
        doctor_a.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        complaint_key="copilot.test.complaint",
    )
    with pytest.raises(ClinicalEncounterConcurrencyError):
        await repo.save(stale)


@pytest.mark.asyncio
async def test_wrong_organization_create_masked_as_not_found(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
) -> None:
    org, doctor_a, _, patient = await _seed_org_context(db_session, user_repository, patient_repository)
    service = _service(db_session)
    with pytest.raises(NotFoundError):
        await service.create_encounter(
            doctor_a.id,
            UserRole.DOCTOR,
            patient_id=patient.id,
            organization_id=uuid4(),
            specialty_key="cardiology",
        )
