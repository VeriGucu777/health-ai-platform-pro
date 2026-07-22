"""Health measurement analytics API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.reference_ranges import ANALYTICS_DISCLAIMER

TrendDirection = Literal["increasing", "decreasing", "stable", "insufficient_data"]
TargetRangeStatus = Literal[
    "within_reference_range",
    "below_reference_range",
    "above_reference_range",
    "not_applicable",
]
AnalyticsPeriod = Literal["daily", "weekly", "monthly"]
HealthMeasurementMetric = Literal[
    "blood_glucose",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "weight_kg",
    "insulin_units",
    "exercise_minutes",
]


class MetricStatisticsResponse(BaseModel):
    """Aggregated statistics for one trackable metric."""

    metric: str
    measurement_count: int
    average: Decimal | None = None
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    trend_direction: TrendDirection
    target_range_status: TargetRangeStatus

    model_config = ConfigDict(from_attributes=True)


class PeriodSummaryResponse(BaseModel):
    """Aggregated statistics for one UTC period bucket."""

    period_start: datetime
    period_end: datetime
    measurement_count: int
    metrics: list[MetricStatisticsResponse]


class HealthMeasurementSummaryResponse(BaseModel):
    """Overall analytics summary for one patient."""

    patient_id: UUID
    metric: HealthMeasurementMetric | None = None
    date_from: datetime
    date_to: datetime
    total_measurement_count: int
    overall: list[MetricStatisticsResponse]
    disclaimer: str = Field(
        default=ANALYTICS_DISCLAIMER,
        description=(
            "Informational tracking disclaimer. Analytics and reference ranges are not "
            "a medical diagnosis or treatment recommendation."
        ),
    )


class HealthMeasurementTrendsResponse(HealthMeasurementSummaryResponse):
    """Period-bucketed analytics summary for one patient."""

    period: AnalyticsPeriod
    periods: list[PeriodSummaryResponse]
