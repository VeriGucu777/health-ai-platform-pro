"""Informational reference ranges for health measurement analytics.

These values are tracking references only. They are not medical diagnoses,
treatment recommendations, or clinical decisions.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MetricReferenceRange:
    """Inclusive informational reference range for a trackable metric."""

    lower: Decimal
    upper: Decimal
    unit: str


@dataclass(frozen=True)
class GlucoseInsightThresholds:
    """Informational adult glucose thresholds for a specific measurement context."""

    urgent_low_below: Decimal
    warning_low_below: Decimal
    normal_lower: Decimal
    normal_upper: Decimal
    warning_high_above: Decimal
    urgent_high_above: Decimal


@dataclass(frozen=True)
class NumericInsightThresholds:
    """Informational adult thresholds for a single numeric metric."""

    urgent_low_below: Decimal
    warning_low_below: Decimal | None
    normal_lower: Decimal
    normal_upper: Decimal
    warning_high_above: Decimal
    urgent_high_above: Decimal


ANALYTICS_DISCLAIMER = (
    "Analytics and reference ranges are provided for tracking and decision-support "
    "purposes only. They are not a medical diagnosis, treatment recommendation, "
    "or substitute for professional medical advice."
)

INSIGHTS_DISCLAIMER = (
    "Clinical insights and health alerts are informational tracking summaries only. "
    "They are not a diagnosis and do not replace evaluation by a qualified "
    "healthcare professional. Urgent alerts suggest that prompt professional "
    "evaluation should be considered; they do not confirm an emergency condition. "
    "If severe symptoms are present, follow local emergency guidance."
)

METRIC_REFERENCE_RANGES: dict[str, MetricReferenceRange] = {
    "blood_glucose": MetricReferenceRange(
        lower=Decimal("70"),
        upper=Decimal("140"),
        unit="mg/dL",
    ),
    "systolic_pressure": MetricReferenceRange(
        lower=Decimal("90"),
        upper=Decimal("120"),
        unit="mmHg",
    ),
    "diastolic_pressure": MetricReferenceRange(
        lower=Decimal("60"),
        upper=Decimal("80"),
        unit="mmHg",
    ),
    "heart_rate": MetricReferenceRange(
        lower=Decimal("60"),
        upper=Decimal("100"),
        unit="bpm",
    ),
}

TRACKABLE_METRICS: tuple[str, ...] = (
    "blood_glucose",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "weight_kg",
    "insulin_units",
    "exercise_minutes",
)

INSIGHT_METRICS: tuple[str, ...] = (
    "blood_glucose",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "weight_kg",
)

KNOWN_GLUCOSE_CONTEXTS: frozenset[str] = frozenset({"fasting", "post_meal"})

FASTING_GLUCOSE_THRESHOLDS = GlucoseInsightThresholds(
    urgent_low_below=Decimal("54"),
    warning_low_below=Decimal("70"),
    normal_lower=Decimal("70"),
    normal_upper=Decimal("99"),
    warning_high_above=Decimal("99"),
    urgent_high_above=Decimal("126"),
)

POST_MEAL_GLUCOSE_THRESHOLDS = GlucoseInsightThresholds(
    urgent_low_below=Decimal("54"),
    warning_low_below=Decimal("70"),
    normal_lower=Decimal("70"),
    normal_upper=Decimal("140"),
    warning_high_above=Decimal("140"),
    urgent_high_above=Decimal("181"),
)

GENERIC_GLUCOSE_THRESHOLDS = GlucoseInsightThresholds(
    urgent_low_below=Decimal("54"),
    warning_low_below=Decimal("70"),
    normal_lower=Decimal("70"),
    normal_upper=Decimal("99"),
    warning_high_above=Decimal("99"),
    urgent_high_above=Decimal("181"),
)

SYSTOLIC_PRESSURE_THRESHOLDS = NumericInsightThresholds(
    urgent_low_below=Decimal("90"),
    warning_low_below=None,
    normal_lower=Decimal("90"),
    normal_upper=Decimal("120"),
    warning_high_above=Decimal("120"),
    urgent_high_above=Decimal("140"),
)

DIASTOLIC_PRESSURE_THRESHOLDS = NumericInsightThresholds(
    urgent_low_below=Decimal("60"),
    warning_low_below=None,
    normal_lower=Decimal("60"),
    normal_upper=Decimal("80"),
    warning_high_above=Decimal("80"),
    urgent_high_above=Decimal("90"),
)

RESTING_HEART_RATE_THRESHOLDS = NumericInsightThresholds(
    urgent_low_below=Decimal("50"),
    warning_low_below=Decimal("60"),
    normal_lower=Decimal("60"),
    normal_upper=Decimal("100"),
    warning_high_above=Decimal("100"),
    urgent_high_above=Decimal("121"),
)

WEIGHT_INFO_CHANGE_PERCENT = Decimal("5")
WEIGHT_WARNING_CHANGE_PERCENT = Decimal("10")

MAX_ANALYTICS_DATE_RANGE_DAYS = 366

TREND_STABLE_THRESHOLD_PERCENT = Decimal("5")
