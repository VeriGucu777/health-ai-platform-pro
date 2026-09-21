"""PostgreSQL integration tests for SQLAlchemyRiskAssessmentHistoryRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.dtos.diabetes_risk_assessment import DiabetesRiskAssessmentDTO
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService
from app.application.services.patient_access_policy_service import DefaultPatientAccessPolicy
from app.application.services.risk_assessment_history_persistence import (
    append_risk_assessment_history,
    build_result_snapshot,
)
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.entities.user import UserRole
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.organization.entities import Organization
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from app.infrastructure.database.models.risk_assessment_history import RiskAssessmentHistoryModel
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.organization_repository import SQLAlchemyOrganizationRepository
from app.infrastructure.repositories.patient_assignment_repository import (
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.risk_assessment_history_repository import (
    SQLAlchemyRiskAssessmentHistoryRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_patient, make_user

WINDOW_FROM = datetime(2026, 1, 1, tzinfo=UTC)
WINDOW_TO = datetime(2026, 6, 1, tzinfo=UTC)


def _sample_diabetes_dto(patient_id: UUID) -> DiabetesRiskAssessmentDTO:
    return DiabetesRiskAssessmentDTO(
        patient_id=patient_id,
        date_from=WINDOW_FROM,
        date_to=WINDOW_TO,
        model_version="rule_based_v1",
        assessment_status="insufficient_data",
        risk_level=None,
        score=None,
        probability=None,
        contributing_factors=[],
        missing_inputs=[],
        recommendations=[],
    )


async def _create_org(session: AsyncSession, name: str = "History Clinic") -> Organization:
    repo = SQLAlchemyOrganizationRepository(session)
    return await repo.create(Organization(name=name, slug=f"hist-{uuid.uuid4().hex[:10]}"))


async def _seed_doctor_and_patient(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    *,
    organization_id: UUID | None = None,
    email_suffix: str = "hist",
):
    doctor = await user_repository.create(
        make_user(role=UserRole.DOCTOR, email=f"{email_suffix}-{uuid.uuid4().hex[:8]}@example.test"),
    )
    await db_session.commit()
    patient = await patient_repository.create(
        make_patient(owner_id=doctor.id, organization_id=organization_id),
    )
    await db_session.commit()
    return doctor, patient


async def _append_entity(
    repository: SQLAlchemyRiskAssessmentHistoryRepository,
    *,
    patient_id: UUID,
    evaluator_id: UUID,
    organization_id: UUID | None = None,
    assessment_type: RiskAssessmentType = RiskAssessmentType.DIABETES,
    evaluated_at: datetime | None = None,
    model_version: str = "rule_based_v1",
    result_snapshot: dict | None = None,
) -> RiskAssessmentHistory:
    when = evaluated_at or datetime.now(UTC)
    entry = RiskAssessmentHistory(
        patient_id=patient_id,
        organization_id=organization_id,
        assessment_type=assessment_type,
        assessment_status="completed",
        risk_level="moderate",
        score=42.0,
        probability=None,
        model_kind=RULE_BASED_MODEL_KIND,
        model_version=model_version,
        evaluated_by_user_id=evaluator_id,
        evaluated_at=when,
        result_snapshot=result_snapshot or {"missing_inputs": [], "contributing_factors": []},
    )
    return await repository.append(entry)


async def _count_history_rows(db_session: AsyncSession, patient_id: UUID) -> int:
    stmt = select(func.count()).select_from(RiskAssessmentHistoryModel).where(
        RiskAssessmentHistoryModel.patient_id == patient_id,
    )
    result = await db_session.execute(stmt)
    return int(result.scalar_one())


async def _load_model_by_id(db_session: AsyncSession, row_id: UUID) -> RiskAssessmentHistoryModel | None:
    result = await db_session.execute(
        select(RiskAssessmentHistoryModel).where(RiskAssessmentHistoryModel.id == row_id),
    )
    return result.scalar_one_or_none()


def _access_policy_bundle(session: AsyncSession) -> DefaultPatientAccessPolicy:
    return DefaultPatientAccessPolicy(
        SQLAlchemyPatientRepository(session),
        SQLAlchemyOrganizationMembershipRepository(session),
        SQLAlchemyPatientAssignmentRepository(session),
    )


async def test_append_diabetes_history_persists_to_postgresql(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    org = await _create_org(db_session)
    await db_session.commit()
    doctor, patient = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        organization_id=org.id,
    )
    dto = _sample_diabetes_dto(patient.id)
    expected_snapshot = build_result_snapshot(dto)

    saved = await append_risk_assessment_history(
        risk_assessment_history_repository,
        patient_id=patient.id,
        organization_id=org.id,
        assessment_type=RiskAssessmentType.DIABETES,
        evaluated_by_user_id=doctor.id,
        assessment_dto=dto,
    )
    await db_session.commit()

    row = await _load_model_by_id(db_session, saved.id)
    assert row is not None
    assert row.patient_id == patient.id
    assert row.organization_id == org.id
    assert row.evaluated_by_user_id == doctor.id
    assert row.assessment_type == RiskAssessmentType.DIABETES.value
    assert row.model_kind == RULE_BASED_MODEL_KIND
    assert row.model_version == "rule_based_v1"
    assert row.probability is None
    assert row.result_snapshot == expected_snapshot


async def test_append_multiple_assessment_types_for_same_patient(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    types_versions = (
        (RiskAssessmentType.DIABETES, "rule_based_v1"),
        (RiskAssessmentType.HEART_DISEASE, "heart_rule_based_v1"),
        (RiskAssessmentType.STROKE, "stroke_rule_based_v1"),
    )
    for assessment_type, version in types_versions:
        await _append_entity(
            risk_assessment_history_repository,
            patient_id=patient.id,
            evaluator_id=doctor.id,
            assessment_type=assessment_type,
            model_version=version,
        )
    await db_session.commit()

    assert await _count_history_rows(db_session, patient.id) == 3
    listed = await risk_assessment_history_repository.list_by_patient(patient.id)
    assert {row.assessment_type for row in listed} == set(RiskAssessmentType)


async def test_list_by_patient_orders_newest_first(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    t_old = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    t_mid = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
    t_new = datetime(2025, 12, 1, 12, 0, tzinfo=UTC)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        evaluated_at=t_mid,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        evaluated_at=t_old,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        evaluated_at=t_new,
    )
    await db_session.commit()

    ordered = await risk_assessment_history_repository.list_by_patient(patient.id)
    assert [row.evaluated_at for row in ordered] == [t_new, t_mid, t_old]


async def test_filter_by_assessment_type(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        assessment_type=RiskAssessmentType.DIABETES,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        assessment_type=RiskAssessmentType.STROKE,
        model_version="stroke_rule_based_v1",
    )
    await db_session.commit()

    diabetes_only = await risk_assessment_history_repository.list_by_patient(
        patient.id,
        assessment_type=RiskAssessmentType.DIABETES,
    )
    assert len(diabetes_only) == 1
    assert diabetes_only[0].assessment_type == RiskAssessmentType.DIABETES
    assert await risk_assessment_history_repository.count_by_patient(
        patient.id,
        assessment_type=RiskAssessmentType.DIABETES,
    ) == 1


async def test_filter_by_evaluated_at_date_range(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    inside = datetime(2026, 3, 15, tzinfo=UTC)
    outside = datetime(2024, 1, 1, tzinfo=UTC)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        evaluated_at=inside,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        evaluated_at=outside,
    )
    await db_session.commit()

    date_from = datetime(2026, 1, 1, tzinfo=UTC)
    date_to = datetime(2026, 12, 31, tzinfo=UTC)
    filtered = await risk_assessment_history_repository.list_by_patient(
        patient.id,
        evaluated_at_from=date_from,
        evaluated_at_to=date_to,
    )
    assert len(filtered) == 1
    assert filtered[0].evaluated_at == inside
    assert await risk_assessment_history_repository.count_by_patient(
        patient.id,
        evaluated_at_from=date_from,
        evaluated_at_to=date_to,
    ) == 1


async def test_pagination_and_count_alignment(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(5):
        await _append_entity(
            risk_assessment_history_repository,
            patient_id=patient.id,
            evaluator_id=doctor.id,
            evaluated_at=base + timedelta(days=index),
        )
    await db_session.commit()

    total = await risk_assessment_history_repository.count_by_patient(patient.id)
    assert total == 5

    page1 = await risk_assessment_history_repository.list_by_patient(patient.id, offset=0, limit=2)
    page2 = await risk_assessment_history_repository.list_by_patient(patient.id, offset=2, limit=2)
    page3 = await risk_assessment_history_repository.list_by_patient(patient.id, offset=4, limit=2)
    merged = page1 + page2 + page3
    assert len(merged) == 5
    assert len({row.id for row in merged}) == 5


async def test_patient_isolation_on_list_and_count(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient_a = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        email_suffix="patient-a",
    )
    _, patient_b = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        email_suffix="patient-b",
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient_a.id,
        evaluator_id=doctor.id,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient_b.id,
        evaluator_id=doctor.id,
        assessment_type=RiskAssessmentType.HEART_DISEASE,
        model_version="heart_rule_based_v1",
    )
    await db_session.commit()

    a_rows = await risk_assessment_history_repository.list_by_patient(patient_a.id)
    assert len(a_rows) == 1
    assert a_rows[0].patient_id == patient_a.id
    assert await risk_assessment_history_repository.count_by_patient(patient_b.id) == 1
    assert await risk_assessment_history_repository.count_by_patient(patient_a.id) == 1


async def test_list_by_patient_does_not_leak_other_patients_by_organization(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    org_a = await _create_org(db_session, name="Org A")
    org_b = await _create_org(db_session, name="Org B")
    await db_session.commit()
    doctor, patient_a = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        organization_id=org_a.id,
        email_suffix="org-a-patient",
    )
    _, patient_b = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        organization_id=org_b.id,
        email_suffix="org-b-patient",
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient_a.id,
        evaluator_id=doctor.id,
        organization_id=org_a.id,
    )
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient_b.id,
        evaluator_id=doctor.id,
        organization_id=org_b.id,
        assessment_type=RiskAssessmentType.STROKE,
        model_version="stroke_rule_based_v1",
    )
    await db_session.commit()

    rows = await risk_assessment_history_repository.list_by_patient(patient_a.id)
    assert len(rows) == 1
    assert rows[0].organization_id == org_a.id
    assert rows[0].patient_id == patient_a.id


async def test_inactive_patient_history_rows_remain_in_database(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
    )
    await db_session.commit()
    assert await _count_history_rows(db_session, patient.id) == 1

    loaded = await patient_repository.get_by_id_and_owner(patient.id, doctor.id)
    assert loaded is not None
    loaded.is_active = False
    loaded.touch()
    await patient_repository.update(loaded)
    await db_session.commit()

    assert await patient_repository.get_by_id_and_owner(patient.id, doctor.id) is None
    assert await _count_history_rows(db_session, patient.id) == 1


async def test_patient_hard_delete_restricted_when_history_exists(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("DELETE FROM patients WHERE id = :pid"),
            {"pid": patient.id},
        )
        await db_session.commit()
    await db_session.rollback()


async def test_organization_delete_sets_history_organization_id_null(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    org = await _create_org(db_session)
    await db_session.commit()
    doctor, patient = await _seed_doctor_and_patient(
        db_session,
        user_repository,
        patient_repository,
        organization_id=None,
    )
    saved = await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
        organization_id=org.id,
    )
    await db_session.commit()

    await db_session.execute(text("DELETE FROM organizations WHERE id = :oid"), {"oid": org.id})
    await db_session.commit()

    row = await _load_model_by_id(db_session, saved.id)
    assert row is not None
    assert row.organization_id is None
    assert row.patient_id == patient.id


def test_repository_port_has_no_update_or_delete() -> None:
    assert not hasattr(RiskAssessmentHistoryRepository, "update")
    assert not hasattr(RiskAssessmentHistoryRepository, "delete")
    repo = SQLAlchemyRiskAssessmentHistoryRepository  # type: ignore[assignment]
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")


async def test_rollback_discards_uncommitted_history_row(
    db_session: AsyncSession,
    integration_engine,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    await _append_entity(
        risk_assessment_history_repository,
        patient_id=patient.id,
        evaluator_id=doctor.id,
    )
    await db_session.rollback()

    session_factory = async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as reader:
        assert await _count_history_rows(reader, patient.id) == 0


async def test_invalid_history_append_does_not_persist_row(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    dto = _sample_diabetes_dto(patient.id)
    with pytest.raises(IntegrityError):
        await append_risk_assessment_history(
            risk_assessment_history_repository,
            patient_id=patient.id,
            organization_id=None,
            assessment_type=RiskAssessmentType.DIABETES,
            evaluated_by_user_id=uuid4(),
            assessment_dto=dto,
        )
        await db_session.commit()
    await db_session.rollback()
    assert await _count_history_rows(db_session, patient.id) == 0


async def test_diabetes_service_single_invocation_appends_one_history_row(
    db_session: AsyncSession,
    user_repository: SQLAlchemyUserRepository,
    patient_repository: SQLAlchemyPatientRepository,
    health_measurement_repository,
    medical_record_repository,
    risk_assessment_history_repository: SQLAlchemyRiskAssessmentHistoryRepository,
) -> None:
    """Same request session as production: assess then append once before commit."""
    doctor, patient = await _seed_doctor_and_patient(db_session, user_repository, patient_repository)
    service = DiabetesRiskAssessmentService(
        patient_repository,
        health_measurement_repository,
        medical_record_repository,
        _access_policy_bundle(db_session),
        history_repository=risk_assessment_history_repository,
    )
    assessment, _org = await service.assess_diabetes_risk(
        doctor.id,
        UserRole.DOCTOR,
        patient_id=patient.id,
        date_from=WINDOW_FROM,
        date_to=WINDOW_TO,
    )
    assert assessment.assessment_status is not None
    await db_session.commit()
    assert await _count_history_rows(db_session, patient.id) == 1

    rows = await risk_assessment_history_repository.list_by_patient(patient.id)
    assert len(rows) == 1
    assert rows[0].model_kind == RULE_BASED_MODEL_KIND
    assert rows[0].model_version == "rule_based_v1"
    assert rows[0].probability is None
    assert rows[0].result_snapshot is not None
    assert "contributing_factors" in rows[0].result_snapshot