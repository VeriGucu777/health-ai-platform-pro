"""Health measurement analytics application DTOs."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.core.reference_ranges import ANALYTICS_DISCLAIMER


class MetricStatisticsDTO(BaseSchema):
    """Aggregated statistics for a single trackable metric."""

    metric: str
    measurement_count: int
    average: Decimal | None = None
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    trend_direction: str
    target_range_status: str


class PeriodSummaryDTO(BaseSchema):
    """Aggregated statistics for a UTC time bucket."""

    period_start: datetime
    period_end: datetime
    measurement_count: int
    metrics: list[MetricStatisticsDTO]


class HealthMeasurementSummaryDTO(BaseSchema):
    """Overall analytics summary for one patient."""

    patient_id: UUID
    metric: str | None
    date_from: datetime
    date_to: datetime
    total_measurement_count: int
    overall: list[MetricStatisticsDTO]
    disclaimer: str = ANALYTICS_DISCLAIMER


class HealthMeasurementTrendsDTO(HealthMeasurementSummaryDTO):
    """Period-bucketed analytics summary for one patient."""

    period: str
    periods: list[PeriodSummaryDTO]
