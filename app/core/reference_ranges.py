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


ANALYTICS_DISCLAIMER = (
    "Analytics and reference ranges are provided for tracking and decision-support "
    "purposes only. They are not a medical diagnosis, treatment recommendation, "
    "or substitute for professional medical advice."
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

MAX_ANALYTICS_DATE_RANGE_DAYS = 366

TREND_STABLE_THRESHOLD_PERCENT = Decimal("5")
