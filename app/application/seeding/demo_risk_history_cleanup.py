"""Ops-only cleanup for a single mis-assigned demo A1 stroke risk history row."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.application.clinical_child_soft_delete import soft_deactivate_clinical_child
from app.application.seeding.demo_enrichment_legacy_cleanup import EXPECTED_PRODUCTION_PATIENT_IDS
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType

A1_DEMO_PATIENT_ID = EXPECTED_PRODUCTION_PATIENT_IDS["a1"]
A1_CANONICAL_DIABETES_RISK_ID = UUID("c5e166de-7a3e-479d-a34f-b5143cddcdbe")
A1_LEGACY_DIABETES_RISK_ID = UUID("6e5272f5-1879-4e28-aa06-354c31b11232")
A1_WRONG_STROKE_RISK_ID = UUID("d547f028-2425-4247-918d-acccfc53c99a")
A1_CANONICAL_SEED_MARKER = "seed:demo-enrich-a1/risk/primary"

EXPECTED_A1_ACTIVE_RISK_ROWS = 3
EXPECTED_OTHER_DEMO_ACTIVE_RISK_ROWS = 1


@dataclass(frozen=True)
class DemoRiskHistoryCleanupConfig:
    patient_id: UUID = A1_DEMO_PATIENT_ID
    target_risk_id: UUID = A1_WRONG_STROKE_RISK_ID
    canonical_risk_id: UUID = A1_CANONICAL_DIABETES_RISK_ID
    legacy_diabetes_risk_id: UUID = A1_LEGACY_DIABETES_RISK_ID
    verify_production_ids: bool = True


@dataclass
class RiskHistoryProtectedCounts:
    a1_active: int
    a2_active: int
    b1_active: int
    b2_active: int
    canonical_active: bool
    legacy_diabetes_active: bool
    target_stroke_active: bool


@dataclass
class DemoRiskHistoryCleanupGuard:
    ok: bool
    abort_reasons: list[str] = field(default_factory=list)


@dataclass
class DemoRiskHistoryCleanupResult:
    mode: str
    guard: DemoRiskHistoryCleanupGuard
    mutated: bool
    protected_before: RiskHistoryProtectedCounts | None = None
    protected_after: RiskHistoryProtectedCounts | None = None
    abort_reasons: list[str] | None = None


def _seed_marker(row) -> str | None:
    snapshot = row.result_snapshot or {}
    marker = snapshot.get("seed_marker")
    return str(marker).strip() if marker else None


async def _active_counts(
    repository: RiskAssessmentHistoryRepository,
) -> RiskHistoryProtectedCounts:
    a1 = await repository.count_by_patient(A1_DEMO_PATIENT_ID)
    a2 = await repository.count_by_patient(EXPECTED_PRODUCTION_PATIENT_IDS["a2"])
    b1 = await repository.count_by_patient(EXPECTED_PRODUCTION_PATIENT_IDS["b1"])
    b2 = await repository.count_by_patient(EXPECTED_PRODUCTION_PATIENT_IDS["b2"])

    canonical = await repository.get_by_id(A1_CANONICAL_DIABETES_RISK_ID, include_inactive=True)
    legacy = await repository.get_by_id(A1_LEGACY_DIABETES_RISK_ID, include_inactive=True)
    target = await repository.get_by_id(A1_WRONG_STROKE_RISK_ID, include_inactive=True)

    return RiskHistoryProtectedCounts(
        a1_active=a1,
        a2_active=a2,
        b1_active=b1,
        b2_active=b2,
        canonical_active=bool(canonical and canonical.is_active),
        legacy_diabetes_active=bool(legacy and legacy.is_active),
        target_stroke_active=bool(target and target.is_active),
    )


async def validate_demo_risk_history_cleanup_guards(
    repository: RiskAssessmentHistoryRepository,
    *,
    config: DemoRiskHistoryCleanupConfig,
) -> DemoRiskHistoryCleanupGuard:
    reasons: list[str] = []

    target = await repository.get_by_id(config.target_risk_id, include_inactive=True)
    if target is None:
        reasons.append(f"Target risk row {config.target_risk_id} not found.")
    else:
        if target.patient_id != config.patient_id:
            reasons.append(
                f"Target row patient_id {target.patient_id} != expected {config.patient_id}.",
            )
        if target.assessment_type != RiskAssessmentType.STROKE:
            reasons.append(
                f"Target assessment_type {target.assessment_type.value!r} != stroke.",
            )

    canonical = await repository.get_by_id(config.canonical_risk_id, include_inactive=True)
    if canonical is None:
        reasons.append(f"Canonical diabetes risk {config.canonical_risk_id} not found.")
    else:
        if canonical.patient_id != config.patient_id:
            reasons.append("Canonical diabetes risk belongs to unexpected patient.")
        if canonical.assessment_type != RiskAssessmentType.DIABETES:
            reasons.append("Canonical risk is not diabetes.")
        if not canonical.is_active:
            reasons.append("Canonical diabetes risk must remain active.")
        marker = _seed_marker(canonical)
        if marker != A1_CANONICAL_SEED_MARKER:
            reasons.append(
                f"Canonical seed_marker {marker!r} != {A1_CANONICAL_SEED_MARKER!r}.",
            )

    legacy = await repository.get_by_id(config.legacy_diabetes_risk_id, include_inactive=True)
    if legacy is None:
        reasons.append(f"Legacy diabetes risk {config.legacy_diabetes_risk_id} not found.")
    elif not legacy.is_active:
        reasons.append("Legacy diabetes risk must remain active (do not touch).")

    counts = await _active_counts(repository)
    if config.verify_production_ids:
        if counts.a1_active != EXPECTED_A1_ACTIVE_RISK_ROWS:
            reasons.append(
                f"A1 active risk count {counts.a1_active} != expected {EXPECTED_A1_ACTIVE_RISK_ROWS}.",
            )
        for key, active in (
            ("a2", counts.a2_active),
            ("b1", counts.b1_active),
            ("b2", counts.b2_active),
        ):
            if active != EXPECTED_OTHER_DEMO_ACTIVE_RISK_ROWS:
                reasons.append(
                    f"{key.upper()} active risk count {active} != expected "
                    f"{EXPECTED_OTHER_DEMO_ACTIVE_RISK_ROWS}.",
                )

    return DemoRiskHistoryCleanupGuard(ok=not reasons, abort_reasons=reasons)


async def run_demo_risk_history_cleanup(
    *,
    risk_history_repository: RiskAssessmentHistoryRepository,
    config: DemoRiskHistoryCleanupConfig | None = None,
    confirm_cleanup: bool = False,
) -> DemoRiskHistoryCleanupResult:
    """Analyze by default; soft-deactivate only the guarded A1 stroke row when confirmed."""
    cfg = config or DemoRiskHistoryCleanupConfig()
    guard = await validate_demo_risk_history_cleanup_guards(
        risk_history_repository,
        config=cfg,
    )
    protected_before = await _active_counts(risk_history_repository)

    if not confirm_cleanup:
        return DemoRiskHistoryCleanupResult(
            mode="analyze",
            guard=guard,
            mutated=False,
            protected_before=protected_before,
        )

    if not guard.ok:
        return DemoRiskHistoryCleanupResult(
            mode="cleanup_aborted",
            guard=guard,
            mutated=False,
            protected_before=protected_before,
            abort_reasons=guard.abort_reasons,
        )

    target = await risk_history_repository.get_by_id(cfg.target_risk_id, include_inactive=True)
    assert target is not None
    if target.is_active:
        soft_deactivate_clinical_child(target, deactivated_at=datetime.now(UTC))
        await risk_history_repository.update(target)

    protected_after = await _active_counts(risk_history_repository)
    post_ok = (
        protected_after.a1_active == protected_before.a1_active - 1
        and protected_after.a2_active == protected_before.a2_active
        and protected_after.b1_active == protected_before.b1_active
        and protected_after.b2_active == protected_before.b2_active
        and protected_after.canonical_active
        and protected_after.legacy_diabetes_active
        and not protected_after.target_stroke_active
    )
    if not post_ok:
        return DemoRiskHistoryCleanupResult(
            mode="cleanup_verify_failed",
            guard=guard,
            mutated=True,
            protected_before=protected_before,
            protected_after=protected_after,
            abort_reasons=["Post-cleanup verification failed."],
        )

    return DemoRiskHistoryCleanupResult(
        mode="cleanup",
        guard=guard,
        mutated=True,
        protected_before=protected_before,
        protected_after=protected_after,
    )
