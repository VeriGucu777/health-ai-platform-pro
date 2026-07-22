"""Unit tests for health measurement analytics calculations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.analytics.health_measurement_analytics import (
    bucket_measurements,
    compute_metric_statistics,
    compute_target_range_status,
    compute_trend_direction,
    get_period_bounds,
)
from app.domain.entities.health_measurement import HealthMeasurement


def _measurement(
    *,
    measured_at: datetime,
    blood_glucose: Decimal | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
) -> HealthMeasurement:
    return HealthMeasurement(
        owner_id=uuid4(),
        patient_id=uuid4(),
        measured_at=measured_at,
        blood_glucose=blood_glucose,
        systolic_pressure=systolic_pressure,
        diastolic_pressure=diastolic_pressure,
    )


def test_compute_trend_direction_increasing() -> None:
    values = [Decimal("100"), Decimal("110"), Decimal("120"), Decimal("130")]
    assert compute_trend_direction(values) == "increasing"


def test_compute_trend_direction_decreasing() -> None:
    values = [Decimal("130"), Decimal("120"), Decimal("110"), Decimal("100")]
    assert compute_trend_direction(values) == "decreasing"


def test_compute_trend_direction_stable() -> None:
    values = [Decimal("100"), Decimal("101"), Decimal("100"), Decimal("101")]
    assert compute_trend_direction(values) == "stable"


def test_compute_trend_direction_insufficient_data() -> None:
    assert compute_trend_direction([Decimal("100")]) == "insufficient_data"


def test_compute_target_range_status_within_reference_range() -> None:
    assert compute_target_range_status("blood_glucose", Decimal("110")) == "within_reference_range"


def test_compute_target_range_status_not_applicable_for_weight() -> None:
    assert compute_target_range_status("weight_kg", Decimal("75")) == "not_applicable"


def test_compute_metric_statistics_separates_blood_pressure_metrics() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            systolic_pressure=120,
            diastolic_pressure=80,
        ),
        _measurement(
            measured_at=datetime(2026, 8, 11, 8, 0, tzinfo=UTC),
            systolic_pressure=130,
            diastolic_pressure=85,
        ),
    ]

    systolic = compute_metric_statistics(measurements, "systolic_pressure")
    diastolic = compute_metric_statistics(measurements, "diastolic_pressure")

    assert systolic["average"] == Decimal("125")
    assert diastolic["average"] == Decimal("82.5")


def test_bucket_measurements_daily_utc() -> None:
    measurements = [
        _measurement(
            measured_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("100"),
        ),
        _measurement(
            measured_at=datetime(2026, 8, 10, 20, 0, tzinfo=UTC),
            blood_glucose=Decimal("110"),
        ),
        _measurement(
            measured_at=datetime(2026, 8, 11, 8, 0, tzinfo=UTC),
            blood_glucose=Decimal("120"),
        ),
    ]

    buckets = bucket_measurements(measurements, "daily")
    assert len(buckets) == 2
    assert len(buckets[0][2]) == 2
    assert len(buckets[1][2]) == 1


def test_get_period_bounds_weekly_utc() -> None:
    measured_at = datetime(2026, 8, 13, 15, 30, tzinfo=UTC)  # Thursday
    start, end = get_period_bounds(measured_at, "weekly")
    assert start == datetime(2026, 8, 10, 0, 0, tzinfo=UTC)
    assert end.weekday() == 6
