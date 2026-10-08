"""PostgreSQL integration tests for clinical encounter repository."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)
from app.infrastructure.clinical_encounter.exceptions import (
    ClinicalEncounterConcurrencyError,
    ClinicalEncounterConflictError,
    ClinicalEncounterFinalSummaryConflictError,
)
from app.infrastructure.repositories.clinical_encounter_repository import (
    SQLAlchemyClinicalEncounterRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.domain.entities.user import User, UserRole
from app.domain.entities.patient import Patient
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.organization_repository import SQLAlchemyOrganizationRepository
from app.domain.organization.entities import Organization


async def _seed_tenant(session: AsyncSession) -> tuple[User, Organization, Patient]:
    user_repo = SQLAlchemyUserRepository(session)
    org_repo = SQLAlchemyOrganizationRepository(session)
    patient_repo = SQLAlchemyPatientRepository(session)
    user = await user_repo.create(
        User(
            email=f"enc-repo-{uuid4().hex[:8]}@example.test",
            hashed_password="hash",
            first_name="Enc",
            last_name="Doctor",
            role=UserRole.DOCTOR,
        ),
    )
    org = await org_repo.create(Organization(name="Enc Org"))
    patient = await patient_repo.create(
        Patient(
            owner_id=user.id,
            organization_id=org.id,
            first_name="Pat",
            last_name="Test",
            date_of_birth=date(1990, 1, 1),
            gender="female",
        ),
    )
    await session.flush()
    return user, org, patient


def _draft_aggregate(user_id, org_id, patient_id) -> ClinicalEncounterAggregate:
    enc = ClinicalEncounter.create_draft(
        patient_id=patient_id,
        organization_id=org_id,
        clinician_user_id=user_id,
        specialty_key="cardiology",
    )
    return ClinicalEncounterAggregate(
        encounter=enc,
        complaints=(
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="copilot.test.complaint",
                sequence_no=2,
                recorded_at=datetime(2026, 2, 1, tzinfo=UTC),
                recorded_by=user_id,
            ),
            EncounterComplaint(
                encounter_id=enc.id,
                complaint_key="copilot.test.secondary",
                sequence_no=1,
                recorded_at=datetime(2026, 2, 2, tzinfo=UTC),
                recorded_by=user_id,
            ),
        ),
        findings=(
            EncounterFinding(
                encounter_id=enc.id,
                finding_type=FindingType.SYMPTOM,
                finding_key="copilot.test.finding",
                value_numeric=Decimal("1.0"),
                unit="unit",
                source=ClinicalInputSource.CLINICIAN_OBSERVED,
                sequence_no=1,
                recorded_at=datetime(2026, 2, 1, tzinfo=UTC),
                recorded_by=user_id,
            ),
        ),
        question_responses=(
            EncounterQuestionResponse(
                encounter_id=enc.id,
                question_key="copilot.test.q",
                answer_type=QuestionAnswerType.BOOLEAN,
                answer_code="yes",
                sequence_no=1,
                answered_at=datetime(2026, 2, 1, tzinfo=UTC),
                answered_by=user_id,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_add_get_children_order_round_trip(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    saved = await repo.add(_draft_aggregate(user.id, org.id, patient.id))
    loaded = await repo.get_by_id(saved.encounter.id)
    assert loaded is not None
    assert [c.sequence_no for c in loaded.complaints] == [1, 2]
    assert loaded.findings[0].finding_key == "copilot.test.finding"
    assert loaded.question_responses[0].answer_code == "yes"


@pytest.mark.asyncio
async def test_save_increments_version_and_stale_rejected(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    agg = await repo.add(_draft_aggregate(user.id, org.id, patient.id))
    stale = await repo.get_by_id(agg.encounter.id)
    assert stale is not None
    stale.encounter.status = EncounterStatus.ACTIVE
    stale.encounter.started_at = datetime(2026, 3, 1, tzinfo=UTC)
    updated = await repo.save(stale)
    assert updated.encounter.version == 2
    with pytest.raises(ClinicalEncounterConcurrencyError):
        await repo.save(agg)


@pytest.mark.asyncio
async def test_active_lookup_scoped_by_org(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    agg = _draft_aggregate(user.id, org.id, patient.id)
    agg.encounter.status = EncounterStatus.ACTIVE
    agg.encounter.started_at = datetime(2026, 3, 1, tzinfo=UTC)
    await repo.add(agg)
    assert await repo.get_active_for_patient(patient.id, org.id) is not None
    assert await repo.get_active_for_patient(patient.id, uuid4()) is None


@pytest.mark.asyncio
async def test_second_active_encounter_rejected(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    first = _draft_aggregate(user.id, org.id, patient.id)
    first.encounter.status = EncounterStatus.ACTIVE
    first.encounter.started_at = datetime(2026, 3, 1, tzinfo=UTC)
    await repo.add(first)
    second = _draft_aggregate(user.id, org.id, patient.id)
    second.encounter.status = EncounterStatus.ACTIVE
    second.encounter.started_at = datetime(2026, 3, 2, tzinfo=UTC)
    with pytest.raises(ClinicalEncounterConflictError):
        await repo.add(second)


@pytest.mark.asyncio
async def test_final_summary_insert_and_overwrite_rejected(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    agg = _draft_aggregate(user.id, org.id, patient.id)
    saved = await repo.add(agg)
    summary = EncounterFinalSummary.create(
        encounter_id=saved.encounter.id,
        summary_version=1,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
        clinician_note=None,
        finalized_by=user.id,
        finalized_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    with_summary = await repo.save(replace(saved, final_summary=summary))
    assert with_summary.final_summary is not None
    duplicate = EncounterFinalSummary.create(
        encounter_id=saved.encounter.id,
        summary_version=2,
        summary_sections=(EncounterSummarySection(section_key="other"),),
        clinician_note=None,
        finalized_by=user.id,
        finalized_at=datetime(2026, 4, 2, tzinfo=UTC),
    )
    with pytest.raises(ClinicalEncounterFinalSummaryConflictError):
        await repo.save(replace(with_summary, final_summary=duplicate))


@pytest.mark.asyncio
async def test_soft_deleted_child_excluded_on_load(db_session: AsyncSession) -> None:
    user, org, patient = await _seed_tenant(db_session)
    repo = SQLAlchemyClinicalEncounterRepository(db_session)
    agg = await repo.add(_draft_aggregate(user.id, org.id, patient.id))
    loaded = await repo.get_by_id(agg.encounter.id)
    assert loaded is not None
    complaint = loaded.complaints[0]
    deactivated = EncounterComplaint(
        id=complaint.id,
        encounter_id=complaint.encounter_id,
        complaint_key=complaint.complaint_key,
        sequence_no=complaint.sequence_no,
        recorded_at=complaint.recorded_at,
        recorded_by=complaint.recorded_by,
        is_active=False,
        deleted_at=datetime(2026, 5, 1, tzinfo=UTC),
    )
    to_save = replace(
        loaded,
        complaints=(deactivated, *loaded.complaints[1:]),
    )
    await repo.save(to_save)
    reloaded = await repo.get_by_id(agg.encounter.id)
    assert reloaded is not None
    assert len(reloaded.complaints) == 1
