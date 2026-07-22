"""Unit tests for health measurement insight rules."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.analytics.health_measurement_insights import (
    build_alerts,
    build_insights,
    build_recommendations,
    classify_metric_insight,
    compute_overall_status,
)
from app.core.reference_ranges import INSIGHTS_DISCLAIMER
from app.domain.entities.health_measurement import HealthMeasurement


def _measurement(
    *,
    measured_at: datetime,
    blood_glucose: Decimal | None = None,
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
    weight_kg: Decimal | None = None,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        blood_glucose=blood_glucose,
        glucose_context=glucose_context,
        systolic_pressure=systolic_pressure,
        diastolic_pressure=diastolic_pressure,
        heart_rate=heart_rate,
        weight_kg=weight_kg,
    )


def test_fasting_glucose_normal_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("99"),
            glucose_context="fasting",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "normal"
    assert insight["status"] == "within_reference_range"


def test_fasting_glucose_warning_high_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("100"),
            glucose_context="fasting",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "warning"
    assert insight["status"] == "above_reference_range"


def test_fasting_glucose_urgent_high_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("126"),
            glucose_context="fasting",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "urgent"
    assert "Prompt professional evaluation" in str(insight["message"])


def test_post_meal_glucose_normal_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("140"),
            glucose_context="post_meal",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "normal"


def test_post_meal_glucose_warning_high_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("141"),
            glucose_context="post_meal",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "warning"


def test_glucose_missing_context_uses_conservative_interpretation() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("95"),
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["severity"] == "info"
    assert insight["status"] == "context_required"
    assert "glucose context was not recorded" in str(insight["message"])


def test_glucose_unknown_context_requires_context_message() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("95"),
            glucose_context="random",
        )
    ]
    insight = classify_metric_insight(measurements, "blood_glucose")
    assert insight["status"] == "context_required"


def test_systolic_and_diastolic_evaluated_separately() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            systolic_pressure=130,
            diastolic_pressure=75,
        )
    ]
    systolic = classify_metric_insight(measurements, "systolic_pressure")
    diastolic = classify_metric_insight(measurements, "diastolic_pressure")
    assert systolic["severity"] == "warning"
    assert diastolic["severity"] == "normal"


def test_resting_heart_rate_warning_high_boundary() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            heart_rate=101,
        )
    ]
    insight = classify_metric_insight(measurements, "heart_rate")
    assert insight["severity"] == "warning"
    assert "resting heart rate" in str(insight["message"])


def test_weight_never_generates_urgent_severity() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
            weight_kg=Decimal("70"),
        ),
        _measurement(
            measured_at=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
            weight_kg=Decimal("90"),
        ),
    ]
    insight = classify_metric_insight(measurements, "weight_kg")
    assert insight["severity"] == "warning"
    assert insight["severity"] != "urgent"


def test_weight_stable_is_normal() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
            weight_kg=Decimal("70"),
        ),
        _measurement(
            measured_at=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
            weight_kg=Decimal("71"),
        ),
    ]
    insight = classify_metric_insight(measurements, "weight_kg")
    assert insight["severity"] == "normal"


def test_build_recommendations_deduplicates_identical_messages() -> None:
    insights = [
        {
            "metric": "blood_glucose",
            "severity": "warning",
            "message": "warning",
        },
        {
            "metric": "systolic_pressure",
            "severity": "warning",
            "message": "warning",
        },
    ]
    alerts = build_alerts(insights)
    recommendations = build_recommendations(insights, alerts, has_any_measurements=True)
    assert len(alerts) == 2
    assert len(recommendations) == 2
    assert len({item["message"] for item in recommendations}) == 2

    duplicate_alerts = [
        {"metric": "blood_glucose", "severity": "warning", "message": "same"},
        {"metric": "blood_glucose", "severity": "warning", "message": "same"},
    ]
    duplicate_recommendations = build_recommendations(
        insights,
        duplicate_alerts,
        has_any_measurements=True,
    )
    assert len(duplicate_recommendations) == 1


def test_empty_history_recommendation() -> None:
    recommendations = build_recommendations([], [], has_any_measurements=False)
    assert len(recommendations) == 1
    assert "Add more health measurements" in recommendations[0]["message"]


def test_compute_overall_status_urgent_wins() -> None:
    assert compute_overall_status(["normal", "warning", "urgent", "info"]) == "urgent"


def test_build_insights_returns_five_metrics_and_disclaimer_fields() -> None:
    payload = build_insights([])
    assert len(payload["insights"]) == 5
    assert payload["overall_status"] == "info"


def test_recommendations_do_not_contain_prescriptive_language() -> None:
    insights = [
        {
            "metric": "blood_glucose",
            "severity": "urgent",
            "message": "urgent",
        }
    ]
    alerts = build_alerts(insights)
    recommendations = build_recommendations(insights, alerts, has_any_measurements=True)
    combined = " ".join(item["message"] for item in recommendations).lower()
    assert "diagnosis" not in combined
    assert "medication" not in combined
    assert "prescribe" not in combined


def test_mandatory_disclaimer_constant_present() -> None:
    assert "not a diagnosis" in INSIGHTS_DISCLAIMER
    assert "qualified healthcare professional" in INSIGHTS_DISCLAIMER
