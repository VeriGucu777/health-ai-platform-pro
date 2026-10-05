"""Unit tests for A2 canonical risk history repair tooling."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.seeding.demo_a2_canonical_risk_repair import (
    A2_CANONICAL_SEED_MARKER,
    A2_DEMO_PATIENT_ID,
    analyze_demo_a2_canonical_risk_repair,
    run_demo_a2_canonical_risk_repair,
)
from app.domain.entities.patient import Patient
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_risk_assessment_history_repository import (
    InMemoryRiskAssessmentHistoryRepository,
)


@pytest.mark.asyncio
async def test_analyze_detects_missing_score_on_canonical_row():
    patients = InMemoryPatientRepository()
    risk = InMemoryRiskAssessmentHistoryRepository()
    owner_id = uuid4()
    await patients.create(
        Patient(
            id=A2_DEMO_PATIENT_ID,
            owner_id=owner_id,
            first_name="Demo",
            last_name="Cardiac Follow-up Patient",
            date_of_birth=datetime(1966, 9, 3, tzinfo=UTC).date(),
            gender="male",
            notes="seed:demo-enrich-a2",
        ),
    )
    await risk.append(
        RiskAssessmentHistory(
            patient_id=A2_DEMO_PATIENT_ID,
            assessment_type=RiskAssessmentType.HEART_DISEASE,
            assessment_status="insufficient_data",
            risk_level=None,
            score=None,
            model_kind=RULE_BASED_MODEL_KIND,
            model_version="rule_based_v1",
            evaluated_by_user_id=owner_id,
            evaluated_at=datetime(2026, 6, 20, tzinfo=UTC),
            result_snapshot={"seed_marker": A2_CANONICAL_SEED_MARKER},
        ),
    )
    result = await analyze_demo_a2_canonical_risk_repair(
        patient_repository=patients,
        risk_history_repository=risk,
    )
    assert result.guard.ok
    assert result.would_update is True


@pytest.mark.asyncio
async def test_confirm_repair_sets_score_and_factors():
    patients = InMemoryPatientRepository()
    risk = InMemoryRiskAssessmentHistoryRepository()
    owner_id = uuid4()
    await patients.create(
        Patient(
            id=A2_DEMO_PATIENT_ID,
            owner_id=owner_id,
            first_name="Demo",
            last_name="Cardiac Follow-up Patient",
            date_of_birth=datetime(1966, 9, 3, tzinfo=UTC).date(),
            gender="male",
            notes="seed:demo-enrich-a2",
        ),
    )
    row = await risk.append(
        RiskAssessmentHistory(
            patient_id=A2_DEMO_PATIENT_ID,
            assessment_type=RiskAssessmentType.HEART_DISEASE,
            assessment_status="insufficient_data",
            risk_level=None,
            score=None,
            model_kind=RULE_BASED_MODEL_KIND,
            model_version="rule_based_v1",
            evaluated_by_user_id=owner_id,
            evaluated_at=datetime(2026, 6, 20, tzinfo=UTC),
            result_snapshot={"seed_marker": A2_CANONICAL_SEED_MARKER},
        ),
    )
    result = await run_demo_a2_canonical_risk_repair(
        patient_repository=patients,
        risk_history_repository=risk,
        confirm_repair=True,
    )
    assert result.mutated
    updated = await risk.get_by_id(row.id)
    assert updated is not None
    assert updated.score == 58.0
    assert updated.risk_level == "moderate"
    assert updated.result_snapshot.get("contributing_factors")
