"""Ops-only repair for A2 canonical demo heart_disease risk history row."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.application.seeding.demo_clinical_enrichment import (
    MARKER_A2,
    PATIENT_SPECS,
    _demo_risk_seed_fields,
    _snapshot_has_marker,
    a2_demo_cardiac_factors_are_enriched,
)
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType

A2_DEMO_PATIENT_ID = UUID("43382858-a46e-4d2e-a33d-4f86b3c140ed")
A2_CANONICAL_SEED_MARKER = f"{MARKER_A2}/risk/primary"


@dataclass
class DemoA2RiskRepairGuard:
    ok: bool
    abort_reasons: list[str] = field(default_factory=list)


@dataclass
class DemoA2RiskRepairResult:
    mode: str
    guard: DemoA2RiskRepairGuard
    record_id: str | None = None
    would_update: bool = False
    mutated: bool = False
    before_score: float | None = None
    before_risk_level: str | None = None
    after_score: float | None = None
    after_risk_level: str | None = None


def _a2_spec():
    return next(spec for spec in PATIENT_SPECS if spec.key == "a2")


def _needs_repair(row) -> bool:
    if row.assessment_type != RiskAssessmentType.HEART_DISEASE:
        return False
    if row.score is None or row.risk_level is None:
        return True
    snapshot = row.result_snapshot or {}
    if not snapshot.get("contributing_factors"):
        return True
    if not a2_demo_cardiac_factors_are_enriched(snapshot):
        return True
    if row.assessment_status.strip().lower() not in {"completed", "complete"}:
        return True
    return False


async def analyze_demo_a2_canonical_risk_repair(
    *,
    patient_repository: PatientRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    patient_id: UUID = A2_DEMO_PATIENT_ID,
    verify_production_patient_id: bool = True,
) -> DemoA2RiskRepairResult:
    reasons: list[str] = []
    if verify_production_patient_id and patient_id != A2_DEMO_PATIENT_ID:
        reasons.append("patient_id is not the configured A2 demo UUID.")

    patient = await patient_repository.get_by_id(patient_id)
    if patient is None:
        reasons.append("Patient not found.")
        return DemoA2RiskRepairResult(
            mode="analyze",
            guard=DemoA2RiskRepairGuard(ok=False, abort_reasons=reasons),
        )

    if MARKER_A2 not in (patient.notes or ""):
        reasons.append("Patient notes do not contain A2 demo enrichment marker.")

    rows = await risk_history_repository.list_by_patient(
        patient_id,
        include_inactive=True,
        limit=50,
    )
    canonical = [
        row
        for row in rows
        if _snapshot_has_marker(row.result_snapshot, A2_CANONICAL_SEED_MARKER)
    ]
    if len(canonical) != 1:
        reasons.append(
            f"Expected exactly one canonical A2 risk row (found {len(canonical)}).",
        )
        return DemoA2RiskRepairResult(
            mode="analyze",
            guard=DemoA2RiskRepairGuard(ok=not reasons, abort_reasons=reasons),
        )

    row = canonical[0]
    guard = DemoA2RiskRepairGuard(ok=not reasons, abort_reasons=reasons)
    return DemoA2RiskRepairResult(
        mode="analyze",
        guard=guard,
        record_id=str(row.id),
        would_update=_needs_repair(row) if guard.ok else False,
        before_score=row.score,
        before_risk_level=row.risk_level,
    )


async def run_demo_a2_canonical_risk_repair(
    *,
    patient_repository: PatientRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    patient_id: UUID = A2_DEMO_PATIENT_ID,
    verify_production_patient_id: bool = True,
    confirm_repair: bool = False,
) -> DemoA2RiskRepairResult:
    analysis = await analyze_demo_a2_canonical_risk_repair(
        patient_repository=patient_repository,
        risk_history_repository=risk_history_repository,
        patient_id=patient_id,
        verify_production_patient_id=verify_production_patient_id,
    )
    if not confirm_repair:
        return analysis

    if not analysis.guard.ok or not analysis.record_id:
        analysis.mode = "repair_aborted"
        return analysis

    row = await risk_history_repository.get_by_id(
        UUID(analysis.record_id),
        include_inactive=True,
    )
    if row is None or not _snapshot_has_marker(row.result_snapshot, A2_CANONICAL_SEED_MARKER):
        analysis.guard.abort_reasons.append("Canonical row missing at repair time.")
        analysis.guard.ok = False
        analysis.mode = "repair_aborted"
        return analysis

    if not _needs_repair(row):
        analysis.mode = "repair_noop"
        return analysis

    spec = _a2_spec()
    fields = _demo_risk_seed_fields(spec, sub_marker=A2_CANONICAL_SEED_MARKER)
    row.assessment_status = fields["assessment_status"]
    row.risk_level = fields["risk_level"]
    row.score = fields["score"]
    row.probability = fields["probability"]
    row.model_version = fields["model_version"]
    row.result_snapshot = fields["result_snapshot"]
    row.touch()
    await risk_history_repository.update(row)

    analysis.mode = "repair"
    analysis.mutated = True
    analysis.after_score = row.score
    analysis.after_risk_level = row.risk_level
    return analysis
