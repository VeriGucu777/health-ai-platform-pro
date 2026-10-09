"""PostgreSQL: clinical encounter mutations and audit rows share transaction."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.audit_service import AuditService
from app.application.services.clinical_encounter_audit_recorder import (
    ClinicalEncounterAuditRecorder,
)
from app.application.services.clinical_encounter_service import ClinicalEncounterService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.domain.audit.taxonomy import AuditAction, AuditResourceType
from app.domain.clinical_encounter.entities import EncounterSummarySection
from app.domain.entities.user import UserRole
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.application_transaction import AsyncSessionApplicationTransaction
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.clinical_encounter import ClinicalEncounterModel
from app.infrastructure.repositories.audit_log_repository import SQLAlchemyAuditLogRepository
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
from app.domain.organization.entities import Organization
from tests.integration.support.factories import make_patient, make_user
from tests.support.failing_audit_log_repository import FailingAuditLogRepository

_T0 = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)


class _FixedClock:
    def now_utc(self) -> datetime:
        return _T0


async def _seed(db_session: AsyncSession):
    user_repo = SQLAlchemyUserRepository(db_session)
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    patient_repo = SQLAlchemyPatientRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)

    org = await org_repo.create(Organization(name="Audit Enc Org", slug=f"aud-{uuid4().hex[:8]}"))
    doctor = await user_repo.create(make_user(role=UserRole.DOCTOR))
    patient = await patient_repo.create(make_patient(owner_id=doctor.id, organization_id=org.id))
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=doctor.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repo.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=patient.id,
            assignee_user_id=doctor.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await db_session.flush()
    return org, doctor, patient


def _encounter_service(db_session: AsyncSession, audit_repo) -> ClinicalEncounterService:
    patient_repo = SQLAlchemyPatientRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)
    policy = DefaultPatientAccessPolicy(patient_repo, membership_repo, assignment_repo)
    audit = ClinicalEncounterAuditRecorder(AuditService(audit_repo))
    return ClinicalEncounterService(
        SQLAlchemyClinicalEncounterRepository(db_session),
        patient_repo,
        access_policy=policy,
        membership_repository=membership_repo,
        transaction=AsyncSessionApplicationTransaction(db_session),
        clock=_FixedClock(),
        audit_hook=audit,
    )


async def _count_encounters(db_session: AsyncSession) -> int:
    result = await db_session.execute(select(func.count()).select_from(ClinicalEncounterModel))
    return int(result.scalar_one())


async def _count_encounter_audits(db_session: AsyncSession) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(AuditLogModel)
        .where(AuditLogModel.resource_type == AuditResourceType.CLINICAL_ENCOUNTER.value),
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_create_persists_encounter_and_audit_same_commit(db_session: AsyncSession) -> None:
    org, doctor, patient = await _seed(db_session)
    audit_repo = SQLAlchemyAuditLogRepository(db_session)
    service = _encounter_service(db_session, audit_repo)

    created = await service.create_encounter(
        doctor.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )

    assert await _count_encounters(db_session) == 1
    assert await _count_encounter_audits(db_session) == 1
    assert created.encounter.status.value == "active"


@pytest.mark.asyncio
async def test_finalize_persists_summary_status_and_audit(db_session: AsyncSession) -> None:
    org, doctor, patient = await _seed(db_session)
    audit_repo = SQLAlchemyAuditLogRepository(db_session)
    service = _encounter_service(db_session, audit_repo)
    enc = await service.create_encounter(
        doctor.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        organization_id=org.id,
        specialty_key="cardiology",
    )
    finalized = await service.finalize_encounter(
        doctor.id,
        UserRole.DOCTOR,
        enc.encounter.id,
        summary_sections=(EncounterSummarySection(section_key="assessment"),),
    )
    assert finalized.final_summary is not None
    assert finalized.encounter.status.value == "finalized"
    audits = await _count_encounter_audits(db_session)
    assert audits >= 2
    result = await db_session.execute(
        select(AuditLogModel).where(
            AuditLogModel.resource_type == AuditResourceType.CLINICAL_ENCOUNTER.value,
            AuditLogModel.action == AuditAction.UPDATE.value,
        ),
    )
    rows = list(result.scalars().all())
    assert any(r.metadata_json and r.metadata_json.get("operation") == "encounter_finalized" for r in rows)


@pytest.mark.asyncio
async def test_audit_append_failure_rolls_back_encounter_create(db_session: AsyncSession) -> None:
    org, doctor, patient = await _seed(db_session)
    service = _encounter_service(db_session, FailingAuditLogRepository())
    encounters_before = await _count_encounters(db_session)
    audits_before = await _count_encounter_audits(db_session)

    with pytest.raises(RuntimeError):
        await service.create_encounter(
            doctor.id,
            UserRole.DOCTOR,
            patient_id=patient.id,
            organization_id=org.id,
            specialty_key="cardiology",
        )

    assert await _count_encounters(db_session) == encounters_before
    assert await _count_encounter_audits(db_session) == audits_before
