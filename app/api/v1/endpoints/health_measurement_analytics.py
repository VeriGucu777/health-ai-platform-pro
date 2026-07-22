"""Health measurement analytics endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_health_measurement_analytics_service
from app.api.schemas.health_measurement_analytics import (
    AnalyticsPeriod,
    HealthMeasurementMetric,
    HealthMeasurementSummaryResponse,
    HealthMeasurementTrendsResponse,
    MetricStatisticsResponse,
    PeriodSummaryResponse,
)
from app.application.dtos.health_measurement_analytics import (
    HealthMeasurementSummaryDTO,
    HealthMeasurementTrendsDTO,
)
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)

router = APIRouter()


def _metric_statistics_response(item) -> MetricStatisticsResponse:
    return MetricStatisticsResponse.model_validate(item.model_dump())


def _summary_response(data: HealthMeasurementSummaryDTO) -> HealthMeasurementSummaryResponse:
    return HealthMeasurementSummaryResponse(
        patient_id=data.patient_id,
        metric=data.metric,
        date_from=data.date_from,
        date_to=data.date_to,
        total_measurement_count=data.total_measurement_count,
        overall=[_metric_statistics_response(item) for item in data.overall],
        disclaimer=data.disclaimer,
    )


def _trends_response(data: HealthMeasurementTrendsDTO) -> HealthMeasurementTrendsResponse:
    return HealthMeasurementTrendsResponse(
        patient_id=data.patient_id,
        metric=data.metric,
        date_from=data.date_from,
        date_to=data.date_to,
        total_measurement_count=data.total_measurement_count,
        overall=[_metric_statistics_response(item) for item in data.overall],
        disclaimer=data.disclaimer,
        period=data.period,
        periods=[
            PeriodSummaryResponse(
                period_start=period.period_start,
                period_end=period.period_end,
                measurement_count=period.measurement_count,
                metrics=[_metric_statistics_response(item) for item in period.metrics],
            )
            for period in data.periods
        ],
    )


@router.get(
    "/summary",
    response_model=HealthMeasurementSummaryResponse,
    summary="Get health measurement analytics summary",
)
async def get_health_measurement_summary(
    current_user: CurrentUser,
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
    patient_id: UUID,
    metric: HealthMeasurementMetric | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HealthMeasurementSummaryResponse:
    """Return overall analytics for one owned patient within the requested UTC date range."""
    summary = await analytics_service.get_summary(
        current_user.id,
        patient_id=patient_id,
        metric=metric,
        date_from=date_from,
        date_to=date_to,
    )
    return _summary_response(summary)


@router.get(
    "/trends",
    response_model=HealthMeasurementTrendsResponse,
    summary="Get health measurement analytics trends",
)
async def get_health_measurement_trends(
    current_user: CurrentUser,
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
    patient_id: UUID,
    period: AnalyticsPeriod,
    metric: HealthMeasurementMetric | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HealthMeasurementTrendsResponse:
    """Return period-bucketed analytics for one owned patient within the requested UTC date range."""
    trends = await analytics_service.get_trends(
        current_user.id,
        patient_id=patient_id,
        period=period,
        metric=metric,
        date_from=date_from,
        date_to=date_to,
    )
    return _trends_response(trends)
