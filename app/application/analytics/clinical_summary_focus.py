"""Infer clinical summary ordering focus from authorized evidence (no patient UUID hacks)."""

from __future__ import annotations

from typing import Literal

from app.application.analytics.clinical_timeline_rules import IMAGING_RECORD_TYPES, LAB_RESULT_RECORD_TYPES
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.domain.risk.enums import RiskAssessmentType

SummaryFocus = Literal["diabetes", "cardiac", "stroke", "general"]


def infer_clinical_summary_focus(bundle: ClinicalEvidenceBundle) -> SummaryFocus:
    """Score diabetes, cardiac, and stroke signals; pick a deterministic focus."""
    scores: dict[SummaryFocus, int] = {
        "diabetes": 0,
        "cardiac": 0,
        "stroke": 0,
        "general": 0,
    }

    for row in bundle.risk_assessment_history:
        if row.assessment_status != "complete":
            continue
        if row.assessment_type == RiskAssessmentType.DIABETES:
            scores["diabetes"] += 3
        elif row.assessment_type == RiskAssessmentType.HEART_DISEASE:
            scores["cardiac"] += 3
        elif row.assessment_type == RiskAssessmentType.STROKE:
            scores["stroke"] += 3

    for record in bundle.medical_records:
        blob = " ".join(
            part
            for part in (record.title, record.diagnosis, record.description, record.treatment)
            if part
        ).lower()
        if any(token in blob for token in ("lipid", "ldl", "hdl", "triglyceride", "cardiac", "cardiovascular")):
            scores["cardiac"] += 2
        if any(token in blob for token in ("echocardiograph", "ekokardiyografi", "echo ")):
            scores["cardiac"] += 2
        if any(token in blob for token in ("brain", "neuro", "stroke", "iskemik", "hemipares")):
            scores["stroke"] += 2
        if any(token in blob for token in ("hba1c", "diabetes", "metabolic laboratory", "glucose logging")):
            scores["diabetes"] += 2
        if record.record_type.strip().lower() in IMAGING_RECORD_TYPES and "brain" in blob:
            scores["stroke"] += 1
        if record.record_type.strip().lower() in LAB_RESULT_RECORD_TYPES and "lipid" in blob:
            scores["cardiac"] += 1

    fasting_glucose = sum(
        1
        for measurement in bundle.health_measurements
        if measurement.blood_glucose is not None
        and (measurement.glucose_context or "").strip().lower() == "fasting"
    )
    if fasting_glucose >= 2 and scores["cardiac"] < scores["diabetes"] + 2:
        scores["diabetes"] += 1

    clinical_scores = {key: scores[key] for key in ("diabetes", "cardiac", "stroke")}
    best = max(clinical_scores.values())
    if best == 0:
        return "general"

    winners = [key for key, value in clinical_scores.items() if value == best]
    if len(winners) == 1:
        return winners[0]

    latest_type = _latest_complete_risk_type(bundle)
    if latest_type == RiskAssessmentType.HEART_DISEASE and "cardiac" in winners:
        return "cardiac"
    if latest_type == RiskAssessmentType.STROKE and "stroke" in winners:
        return "stroke"
    if latest_type == RiskAssessmentType.DIABETES and "diabetes" in winners:
        return "diabetes"

    priority: tuple[SummaryFocus, ...] = ("cardiac", "stroke", "diabetes")
    for focus in priority:
        if focus in winners:
            return focus
    return "general"


def _latest_complete_risk_type(bundle: ClinicalEvidenceBundle) -> RiskAssessmentType | None:
    latest = None
    latest_at = None
    for row in bundle.risk_assessment_history:
        if row.assessment_status != "complete":
            continue
        if latest_at is None or row.evaluated_at > latest_at:
            latest_at = row.evaluated_at
            latest = row.assessment_type
    return latest
