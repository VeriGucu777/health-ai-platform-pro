"""Pure calculation helpers for health measurement analytics."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from app.core.reference_ranges import (
    KNOWN_GLUCOSE_CONTEXTS,
    METRIC_REFERENCE_RANGES,
    TREND_STABLE_THRESHOLD_PERCENT,
    TRACKABLE_METRICS,
)

MIN_DIRECTIONAL_TREND_SAMPLE_COUNT = 3
from app.domain.entities.health_measurement import HealthMeasurement

TrendDirection = Literal["increasing", "decreasing", "stable", "insufficient_data"]
TargetRangeStatus = Literal[
    "within_reference_range",
    "below_reference_range",
    "above_reference_range",
    "not_applicable",
]
AnalyticsPeriod = Literal["daily", "weekly", "monthly"]


def extract_metric_value(measurement: HealthMeasurement, metric: str) -> Decimal | None:
    """Return a metric value as Decimal when present."""
    value = getattr(measurement, metric, None)
    if value is None:
        return None
    return Decimal(value) if not isinstance(value, Decimal) else value


def compute_metric_statistics(
    measurements: list[HealthMeasurement],
    metric: str,
) -> dict[str, object]:
    """Compute count, average, min, max, trend, and reference range status."""
    values = [
        value
        for measurement in measurements
        if (value := extract_metric_value(measurement, metric)) is not None
    ]

    count = len(values)
    if count == 0:
        return {
            "metric": metric,
            "measurement_count": 0,
            "average": None,
            "minimum": None,
            "maximum": None,
            "trend_direction": "insufficient_data",
            "target_range_status": "not_applicable",
        }

    average = sum(values, Decimal("0")) / Decimal(count)
    minimum = min(values)
    maximum = max(values)

    return {
        "metric": metric,
        "measurement_count": count,
        "average": average,
        "minimum": minimum,
        "maximum": maximum,
        "trend_direction": compute_trend_direction(values),
        "target_range_status": compute_target_range_status(metric, average),
    }


def compute_trend_direction(values: list[Decimal]) -> TrendDirection:
    """Compare early and late averages to determine trend direction."""
    if len(values) < 2:
        return "insufficient_data"

    split_index = (len(values) + 1) // 2
    early_values = values[:split_index]
    late_values = values[split_index:]
    early_avg = sum(early_values, Decimal("0")) / Decimal(len(early_values))
    late_avg = sum(late_values, Decimal("0")) / Decimal(len(late_values))

    if early_avg == 0:
        absolute_delta = late_avg - early_avg
        if abs(absolute_delta) < Decimal("1"):
            return "stable"
        return "increasing" if absolute_delta > 0 else "decreasing"

    delta_percent = ((late_avg - early_avg) / abs(early_avg)) * Decimal("100")
    if abs(delta_percent) < TREND_STABLE_THRESHOLD_PERCENT:
        return "stable"
    return "increasing" if delta_percent > 0 else "decreasing"


def compute_target_range_status(metric: str, average: Decimal | None) -> TargetRangeStatus:
    """Compare the average against informational reference ranges."""
    if average is None:
        return "not_applicable"

    reference_range = METRIC_REFERENCE_RANGES.get(metric)
    if reference_range is None:
        return "not_applicable"

    if average < reference_range.lower:
        return "below_reference_range"
    if average > reference_range.upper:
        return "above_reference_range"
    return "within_reference_range"


def bucket_measurements(
    measurements: list[HealthMeasurement],
    period: AnalyticsPeriod,
) -> list[tuple[datetime, datetime, list[HealthMeasurement]]]:
    """Group measurements into UTC period buckets ordered oldest to newest."""
    buckets: dict[str, tuple[datetime, datetime, list[HealthMeasurement]]] = {}

    for measurement in measurements:
        bucket_start, bucket_end = get_period_bounds(measurement.measured_at, period)
        key = bucket_start.isoformat()
        if key not in buckets:
            buckets[key] = (bucket_start, bucket_end, [])
        buckets[key][2].append(measurement)

    return sorted(buckets.values(), key=lambda item: item[0])


def get_period_bounds(measured_at: datetime, period: AnalyticsPeriod) -> tuple[datetime, datetime]:
    """Return inclusive UTC start/end datetimes for a measurement timestamp."""
    if measured_at.tzinfo is None:
        measured_at = measured_at.replace(tzinfo=UTC)
    else:
        measured_at = measured_at.astimezone(UTC)

    if period == "daily":
        start = measured_at.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1) - timedelta(microseconds=1)
        return start, end

    if period == "weekly":
        start_date = measured_at.date() - timedelta(days=measured_at.weekday())
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end = start + timedelta(days=7) - timedelta(microseconds=1)
        return start, end

    start = measured_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(microseconds=1)
    return start, end


def metrics_to_include(metric_filter: str | None) -> tuple[str, ...]:
    """Return the metric list to include in analytics output."""
    if metric_filter is None:
        return TRACKABLE_METRICS
    return (metric_filter,)


def normalize_glucose_context(raw: str | None) -> str | None:
    """Return a known glucose context key or None when context is missing/unknown."""
    if raw is None:
        return None
    key = raw.strip().lower()
    if key in KNOWN_GLUCOSE_CONTEXTS:
        return key
    return None


def group_blood_glucose_by_comparable_context(
    measurements: list[HealthMeasurement],
) -> dict[str, list[HealthMeasurement]]:
    """Group glucose measurements by explicit fasting/post_meal context only."""
    groups: dict[str, list[HealthMeasurement]] = {}
    for measurement in measurements:
        if extract_metric_value(measurement, "blood_glucose") is None:
            continue
        context = normalize_glucose_context(measurement.glucose_context)
        if context is None:
            continue
        groups.setdefault(context, []).append(measurement)
    for context in groups:
        groups[context].sort(key=lambda item: item.measured_at)
    return groups


def sort_measurements_chronologically(
    measurements: list[HealthMeasurement],
) -> list[HealthMeasurement]:
    """Return measurements ordered oldest to newest by measured_at."""
    return sorted(measurements, key=lambda item: item.measured_at)


def data_period_bounds(
    measurements: list[HealthMeasurement],
) -> tuple[datetime | None, datetime | None]:
    """Return UTC min/max measured_at for a non-empty measurement list."""
    if not measurements:
        return None, None
    ordered = sort_measurements_chronologically(measurements)
    start = ordered[0].measured_at
    end = ordered[-1].measured_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    else:
        start = start.astimezone(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    else:
        end = end.astimezone(UTC)
    return start, end
