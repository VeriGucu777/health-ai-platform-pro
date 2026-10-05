"""Tests for A1 demo stroke risk history cleanup tooling."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.seeding.demo_enrichment_legacy_cleanup import EXPECTED_PRODUCTION_PATIENT_IDS
from app.application.seeding.demo_risk_history_cleanup import (
    A1_CANONICAL_DIABETES_RISK_ID,
    A1_CANONICAL_SEED_MARKER,
    A1_DEMO_PATIENT_ID,
    A1_LEGACY_DIABETES_RISK_ID,
    A1_WRONG_STROKE_RISK_ID,
    DemoRiskHistoryCleanupConfig,
    run_demo_risk_history_cleanup,
    validate_demo_risk_history_cleanup_guards,
)
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from tests.support.memory_risk_assessment_history_repository import (
    InMemoryRiskAssessmentHistoryRepository,
)


def _row(
    *,
    row_id,
    patient_id,
    assessment_type: RiskAssessmentType,
    seed_marker: str | None = None,
    is_active: bool = True,
) -> RiskAssessmentHistory:
    now = datetime.now(UTC)
    snapshot = {"seed_marker": seed_marker} if seed_marker else None
    return RiskAssessmentHistory(
        id=row_id,
        patient_id=patient_id,
        assessment_type=assessment_type,
        assessment_status="completed",
        model_kind=RULE_BASED_MODEL_KIND,
        model_version="rule_based_v1",
        evaluated_by_user_id=uuid4(),
        evaluated_at=now,
        result_snapshot=snapshot,
        is_active=is_active,
    )


async def _production_like_fixture(
    risk: InMemoryRiskAssessmentHistoryRepository,
) -> None:
    evaluator = uuid4()
    now = datetime.now(UTC)

    async def _append_for_patient(patient_id, rows: list[RiskAssessmentHistory]) -> None:
        for entry in rows:
            entry.evaluated_by_user_id = evaluator
            entry.evaluated_at = now
            await risk.append(entry)

    await _append_for_patient(
        A1_DEMO_PATIENT_ID,
        [
            _row(
                row_id=A1_CANONICAL_DIABETES_RISK_ID,
                patient_id=A1_DEMO_PATIENT_ID,
                assessment_type=RiskAssessmentType.DIABETES,
                seed_marker=A1_CANONICAL_SEED_MARKER,
            ),
            _row(
                row_id=A1_LEGACY_DIABETES_RISK_ID,
                patient_id=A1_DEMO_PATIENT_ID,
                assessment_type=RiskAssessmentType.DIABETES,
            ),
            _row(
                row_id=A1_WRONG_STROKE_RISK_ID,
                patient_id=A1_DEMO_PATIENT_ID,
                assessment_type=RiskAssessmentType.STROKE,
            ),
        ],
    )
    for key in ("a2", "b1", "b2"):
        await _append_for_patient(
            EXPECTED_PRODUCTION_PATIENT_IDS[key],
            [
                _row(
                    row_id=uuid4(),
                    patient_id=EXPECTED_PRODUCTION_PATIENT_IDS[key],
                    assessment_type=RiskAssessmentType.DIABETES,
                    seed_marker=f"seed:demo-enrich-{key}/risk/primary",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_analyze_does_not_mutate():
    risk = InMemoryRiskAssessmentHistoryRepository()
    await _production_like_fixture(risk)
    before = len(risk.rows)
    result = await run_demo_risk_history_cleanup(
        risk_history_repository=risk,
        confirm_cleanup=False,
    )
    assert result.mode == "analyze"
    assert not result.mutated
    assert result.guard.ok
    assert len(risk.rows) == before
    target = await risk.get_by_id(A1_WRONG_STROKE_RISK_ID, include_inactive=True)
    assert target is not None and target.is_active


@pytest.mark.asyncio
async def test_confirm_soft_deactivates_only_target_stroke():
    risk = InMemoryRiskAssessmentHistoryRepository()
    await _production_like_fixture(risk)
    result = await run_demo_risk_history_cleanup(
        risk_history_repository=risk,
        confirm_cleanup=True,
    )
    assert result.mode == "cleanup"
    assert result.mutated
    assert result.protected_after is not None
    assert not result.protected_after.target_stroke_active
    assert result.protected_after.canonical_active
    assert result.protected_after.legacy_diabetes_active
    assert result.protected_after.a1_active == 2
    assert result.protected_after.a2_active == 1
    assert result.protected_after.b1_active == 1
    assert result.protected_after.b2_active == 1

    canonical = await risk.get_by_id(A1_CANONICAL_DIABETES_RISK_ID)
    assert canonical is not None
    legacy = await risk.get_by_id(A1_LEGACY_DIABETES_RISK_ID)
    assert legacy is not None
    assert await risk.get_by_id(A1_WRONG_STROKE_RISK_ID) is None
    inactive = await risk.get_by_id(A1_WRONG_STROKE_RISK_ID, include_inactive=True)
    assert inactive is not None and not inactive.is_active


@pytest.mark.asyncio
async def test_guard_aborts_wrong_assessment_type():
    risk = InMemoryRiskAssessmentHistoryRepository()
    await _production_like_fixture(risk)
    wrong = await risk.get_by_id(A1_WRONG_STROKE_RISK_ID, include_inactive=True)
    assert wrong is not None
    wrong.assessment_type = RiskAssessmentType.DIABETES
    await risk.update(wrong)
    guard = await validate_demo_risk_history_cleanup_guards(
        risk,
        config=DemoRiskHistoryCleanupConfig(verify_production_ids=True),
    )
    assert not guard.ok
    result = await run_demo_risk_history_cleanup(
        risk_history_repository=risk,
        confirm_cleanup=True,
    )
    assert result.mode == "cleanup_aborted"
    assert not result.mutated
