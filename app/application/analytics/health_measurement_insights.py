"""Pure rule engine for health measurement clinical insights."""

from decimal import Decimal
from typing import Literal

from app.application.analytics.health_measurement_analytics import (
    compute_metric_statistics,
    extract_metric_value,
)
from app.core.reference_ranges import (
    DIASTOLIC_PRESSURE_THRESHOLDS,
    FASTING_GLUCOSE_THRESHOLDS,
    GENERIC_GLUCOSE_THRESHOLDS,
    INSIGHT_METRICS,
    KNOWN_GLUCOSE_CONTEXTS,
    POST_MEAL_GLUCOSE_THRESHOLDS,
    RESTING_HEART_RATE_THRESHOLDS,
    SYSTOLIC_PRESSURE_THRESHOLDS,
    WEIGHT_INFO_CHANGE_PERCENT,
    WEIGHT_WARNING_CHANGE_PERCENT,
)
from app.domain.entities.health_measurement import HealthMeasurement

InsightSeverity = Literal["normal", "info", "warning", "urgent"]
InsightStatus = Literal[
    "within_reference_range",
    "below_reference_range",
    "above_reference_range",
    "insufficient_data",
    "context_required",
    "stable_trend",
    "increasing_trend",
    "decreasing_trend",
]
RecommendationCategory = Literal["monitoring", "follow_up", "tracking"]

SEVERITY_RANK = {"normal": 0, "info": 1, "warning": 2, "urgent": 3}

EMPTY_HISTORY_RECOMMENDATION = (
    "monitoring",
    "Add more health measurements over time to generate meaningful insights.",
    (),
)


def extract_latest_measurement(
    measurements: list[HealthMeasurement],
    metric: str,
) -> HealthMeasurement | None:
    """Return the most recent measurement that includes the requested metric."""
    candidates = [
        measurement
        for measurement in measurements
        if extract_metric_value(measurement, metric) is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.measured_at)


def extract_latest_value(
    measurements: list[HealthMeasurement],
    metric: str,
) -> Decimal | None:
    """Return the latest non-null metric value."""
    latest_measurement = extract_latest_measurement(measurements, metric)
    if latest_measurement is None:
        return None
    return extract_metric_value(latest_measurement, metric)


def compute_overall_status(severities: list[InsightSeverity]) -> InsightSeverity:
    """Return the highest severity across insight items."""
    if not severities:
        return "info"
    return max(severities, key=lambda item: SEVERITY_RANK[item])


def classify_metric_insight(
    measurements: list[HealthMeasurement],
    metric: str,
) -> dict[str, object]:
    """Build one deterministic insight entry for a metric."""
    stats = compute_metric_statistics(measurements, metric)
    latest_value = extract_latest_value(measurements, metric)
    average_value = stats["average"]
    trend_direction = stats["trend_direction"]

    if latest_value is None:
        return {
            "metric": metric,
            "status": "insufficient_data",
            "severity": "info",
            "latest_value": None,
            "average_value": None,
            "trend_direction": "insufficient_data",
            "message": _message_for_no_data(metric),
        }

    if metric == "blood_glucose":
        latest_measurement = extract_latest_measurement(measurements, metric)
        assert latest_measurement is not None
        severity, status, message = _classify_blood_glucose(
            latest_value,
            latest_measurement.glucose_context,
        )
    elif metric == "systolic_pressure":
        severity, status, message = _classify_numeric_metric(
            latest_value,
            SYSTOLIC_PRESSURE_THRESHOLDS,
            metric_label="systolic blood pressure",
            reference_description="general adult blood pressure reference ranges",
        )
    elif metric == "diastolic_pressure":
        severity, status, message = _classify_numeric_metric(
            latest_value,
            DIASTOLIC_PRESSURE_THRESHOLDS,
            metric_label="diastolic blood pressure",
            reference_description="general adult blood pressure reference ranges",
        )
    elif metric == "heart_rate":
        severity, status, message = _classify_numeric_metric(
            latest_value,
            RESTING_HEART_RATE_THRESHOLDS,
            metric_label="resting heart rate",
            reference_description="resting adult heart rate reference ranges",
        )
    elif metric == "weight_kg":
        severity, status, message = _classify_weight(
            measurements,
            trend_direction=str(trend_direction),
        )
    else:
        severity, status, message = "info", "insufficient_data", "Metric insight is not available."

    severity, status, message = _apply_trend_adjustment(
        metric=metric,
        severity=severity,
        status=status,
        trend_direction=str(trend_direction),
        message=message,
    )

    return {
        "metric": metric,
        "status": status,
        "severity": severity,
        "latest_value": latest_value,
        "average_value": average_value,
        "trend_direction": trend_direction,
        "message": message,
    }


def build_alerts(insights: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return warning and urgent insights as alert entries."""
    alerts: list[dict[str, object]] = []
    for insight in insights:
        severity = insight["severity"]
        if severity in {"warning", "urgent"}:
            alerts.append(
                {
                    "metric": insight["metric"],
                    "severity": severity,
                    "message": insight["message"],
                }
            )
    return alerts


def build_recommendations(
    insights: list[dict[str, object]],
    alerts: list[dict[str, object]],
    *,
    has_any_measurements: bool,
) -> list[dict[str, object]]:
    """Build deduplicated, non-prescriptive recommendations."""
    if not has_any_measurements:
        category, message, related_metrics = EMPTY_HISTORY_RECOMMENDATION
        return [
            {
                "category": category,
                "message": message,
                "related_metrics": list(related_metrics),
            }
        ]

    recommendations: list[dict[str, object]] = []
    seen_messages: set[str] = set()

    for alert in alerts:
        recommendation = _recommendation_for_alert(str(alert["metric"]), str(alert["severity"]))
        if recommendation is None:
            continue
        category, message, related_metrics = recommendation
        if message in seen_messages:
            continue
        seen_messages.add(message)
        recommendations.append(
            {
                "category": category,
                "message": message,
                "related_metrics": list(related_metrics),
            }
        )

    return recommendations


def build_insights(measurements: list[HealthMeasurement]) -> dict[str, object]:
    """Compute insights, alerts, recommendations, and overall status."""
    insights = [classify_metric_insight(measurements, metric) for metric in INSIGHT_METRICS]
    alerts = build_alerts(insights)
    has_any_measurements = len(measurements) > 0
    recommendations = build_recommendations(
        insights,
        alerts,
        has_any_measurements=has_any_measurements,
    )
    overall_status = compute_overall_status([insight["severity"] for insight in insights])
    return {
        "overall_status": overall_status,
        "insights": insights,
        "alerts": alerts,
        "recommendations": recommendations,
    }


def _classify_blood_glucose(
    value: Decimal,
    glucose_context: str | None,
) -> tuple[InsightSeverity, InsightStatus, str]:
    context = glucose_context.strip().lower() if isinstance(glucose_context, str) else None
    context_missing = context not in KNOWN_GLUCOSE_CONTEXTS

    if context == "fasting":
        thresholds = FASTING_GLUCOSE_THRESHOLDS
        context_label = "fasting"
    elif context == "post_meal":
        thresholds = POST_MEAL_GLUCOSE_THRESHOLDS
        context_label = "post-meal"
    else:
        thresholds = GENERIC_GLUCOSE_THRESHOLDS
        context_label = None

    severity, status = _classify_against_thresholds(value, thresholds)

    if context_missing:
        if severity == "normal":
            severity = "info"
            status = "context_required"
        elif status == "within_reference_range":
            status = "context_required"
        message = (
            "Blood glucose was evaluated using a conservative generic adult reference range "
            "because glucose context was not recorded. Recording fasting or post-meal context "
            "supports a more meaningful assessment. "
            + _glucose_value_message(value, severity, status, context_label)
        )
        return severity, status, message

    message = _glucose_value_message(value, severity, status, context_label)
    return severity, status, message


def _classify_numeric_metric(
    value: Decimal,
    thresholds,
    *,
    metric_label: str,
    reference_description: str,
) -> tuple[InsightSeverity, InsightStatus, str]:
    severity, status = _classify_against_thresholds(value, thresholds)
    message = (
        f"The latest {metric_label} reading is {_status_phrase(status)} "
        f"based on {reference_description} for informational tracking only. "
        f"This is not a diagnosis."
    )
    if severity == "urgent":
        message += (
            " Prompt professional evaluation should be considered. "
            "If severe symptoms are present, follow local emergency guidance."
        )
    return severity, status, message


def _classify_weight(
    measurements: list[HealthMeasurement],
    *,
    trend_direction: str,
) -> tuple[InsightSeverity, InsightStatus, str]:
    weight_measurements = sorted(
        [
            measurement
            for measurement in measurements
            if extract_metric_value(measurement, "weight_kg") is not None
        ],
        key=lambda item: item.measured_at,
    )
    if len(weight_measurements) < 2:
        return (
            "info",
            "insufficient_data",
            "Not enough weight measurements are available to assess trend meaningfully.",
        )

    earliest = extract_metric_value(weight_measurements[0], "weight_kg")
    latest = extract_metric_value(weight_measurements[-1], "weight_kg")
    assert earliest is not None and latest is not None

    if earliest == 0:
        percent_change = Decimal("0")
    else:
        percent_change = abs((latest - earliest) / earliest * Decimal("100"))

    if trend_direction == "insufficient_data":
        status: InsightStatus = "insufficient_data"
    elif trend_direction == "stable":
        status = "stable_trend"
    elif trend_direction == "increasing":
        status = "increasing_trend"
    else:
        status = "decreasing_trend"

    if percent_change <= WEIGHT_INFO_CHANGE_PERCENT and trend_direction == "stable":
        severity: InsightSeverity = "normal"
        message = (
            "Weight readings appear relatively stable across the selected period. "
            "This trend summary is informational and does not indicate a medical condition."
        )
    elif percent_change <= WEIGHT_WARNING_CHANGE_PERCENT:
        severity = "info"
        message = (
            "Weight readings show a moderate change over the selected period. "
            "Continue routine tracking and discuss significant changes with a qualified "
            "healthcare professional if needed."
        )
    else:
        severity = "warning"
        message = (
            "Weight readings show a notable percentage change over the selected period. "
            "This tracking summary is informational only and does not diagnose a condition "
            "or indicate an emergency."
        )

    return severity, status, message


def _classify_against_thresholds(
    value: Decimal,
    thresholds,
) -> tuple[InsightSeverity, InsightStatus]:
    if value < thresholds.urgent_low_below:
        return "urgent", "below_reference_range"

    if (
        thresholds.warning_low_below is not None
        and value < thresholds.warning_low_below
    ):
        return "warning", "below_reference_range"

    if value >= thresholds.urgent_high_above:
        return "urgent", "above_reference_range"

    if value > thresholds.warning_high_above:
        return "warning", "above_reference_range"

    if thresholds.normal_lower <= value <= thresholds.normal_upper:
        return "normal", "within_reference_range"

    return "info", "within_reference_range"


def _apply_trend_adjustment(
    *,
    metric: str,
    severity: InsightSeverity,
    status: InsightStatus,
    trend_direction: str,
    message: str,
) -> tuple[InsightSeverity, InsightStatus, str]:
    if metric == "weight_kg" or trend_direction in {"insufficient_data", "stable"}:
        return severity, status, message

    if severity != "normal":
        return severity, status, message

    if trend_direction == "increasing":
        return (
            "info",
            "increasing_trend",
            message + " Readings show an increasing trend over the selected period.",
        )

    return (
        "info",
        "decreasing_trend",
        message + " Readings show a decreasing trend over the selected period.",
    )


def _glucose_value_message(
    value: Decimal,
    severity: InsightSeverity,
    status: InsightStatus,
    context_label: str | None,
) -> str:
    context_text = f"{context_label} " if context_label else ""
    base = (
        f"The latest {context_text}blood glucose reading is {_status_phrase(status)} "
        "using general adult reference ranges for informational tracking only. "
        "This is not a diagnosis."
    )
    if severity == "urgent":
        base += (
            " Prompt professional evaluation should be considered. "
            "If severe symptoms are present, follow local emergency guidance."
        )
    return base


def _status_phrase(status: InsightStatus) -> str:
    mapping = {
        "within_reference_range": "within the informational reference range",
        "below_reference_range": "below the informational reference range",
        "above_reference_range": "above the informational reference range",
        "context_required": "recorded without sufficient measurement context",
        "insufficient_data": "not available for assessment",
        "stable_trend": "associated with a stable trend",
        "increasing_trend": "associated with an increasing trend",
        "decreasing_trend": "associated with a decreasing trend",
    }
    return mapping.get(status, "available for review")


def _message_for_no_data(metric: str) -> str:
    labels = {
        "blood_glucose": "blood glucose",
        "systolic_pressure": "systolic blood pressure",
        "diastolic_pressure": "diastolic blood pressure",
        "heart_rate": "resting heart rate",
        "weight_kg": "weight",
    }
    label = labels.get(metric, metric.replace("_", " "))
    return f"No {label} measurements were recorded in the selected date range."


def _recommendation_for_alert(
    metric: str,
    severity: InsightSeverity,
) -> tuple[RecommendationCategory, str, tuple[str, ...]] | None:
    if severity not in {"warning", "urgent"}:
        return None

    labels = {
        "blood_glucose": "blood glucose",
        "systolic_pressure": "systolic blood pressure",
        "diastolic_pressure": "diastolic blood pressure",
        "heart_rate": "resting heart rate",
        "weight_kg": "weight",
    }
    label = labels.get(metric, metric.replace("_", " "))

    if severity == "urgent":
        message = (
            f"Prompt professional evaluation should be considered for recent {label} readings. "
            "If severe symptoms are present, follow local emergency guidance."
        )
        return "follow_up", message, (metric,)

    message = (
        f"Consider sharing recent {label} readings with a qualified healthcare professional "
        "and repeat measurements as appropriate for ongoing tracking."
    )
    return "follow_up", message, (metric,)
