"""Health measurement analytics endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.clinical_child_read_audit import audit_analytics_view
from app.api.deps import ClinicalUser, get_audit_service, get_health_measurement_analytics_service
from app.api.schemas.health_measurement_analytics import (
    AnalyticsPeriod,
    HealthMeasurementMetric,
    HealthMeasurementSummaryResponse,
    HealthMeasurementTrendsResponse,
    MetricStatisticsResponse,
    PeriodSummaryResponse,
)
from app.api.schemas.health_measurement_insights import (
    HealthAlertResponse,
    HealthMeasurementInsightsResponse,
    HealthRecommendationResponse,
    MetricInsightResponse,
)
from app.application.dtos.health_measurement_analytics import (
    HealthMeasurementSummaryDTO,
    HealthMeasurementTrendsDTO,
)
from app.application.dtos.health_measurement_insights import HealthMeasurementInsightsDTO
from app.application.services.audit_service import AuditService
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
    request: Request,
    current_user: ClinicalUser,
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    patient_id: UUID,
    metric: HealthMeasurementMetric | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HealthMeasurementSummaryResponse:
    """Return overall analytics for one owned patient within the requested UTC date range."""
    summary = await audit_analytics_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        analytics_endpoint="summary",
        patient_id=patient_id,
        policy_service=analytics_service,
        date_from=date_from,
        date_to=date_to,
        period=None,
        load=lambda: analytics_service.get_summary(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            metric=metric,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return _summary_response(summary)


@router.get(
    "/trends",
    response_model=HealthMeasurementTrendsResponse,
    summary="Get health measurement analytics trends",
)
async def get_health_measurement_trends(
    request: Request,
    current_user: ClinicalUser,
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    patient_id: UUID,
    period: AnalyticsPeriod,
    metric: HealthMeasurementMetric | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HealthMeasurementTrendsResponse:
    """Return period-bucketed analytics for one owned patient within the requested UTC date range."""
    trends = await audit_analytics_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        analytics_endpoint="trends",
        patient_id=patient_id,
        policy_service=analytics_service,
        date_from=date_from,
        date_to=date_to,
        period=period,
        load=lambda: analytics_service.get_trends(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            period=period,
            metric=metric,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return _trends_response(trends)


def _insights_response(data: HealthMeasurementInsightsDTO) -> HealthMeasurementInsightsResponse:
    return HealthMeasurementInsightsResponse(
        patient_id=data.patient_id,
        date_from=data.date_from,
        date_to=data.date_to,
        overall_status=data.overall_status,
        insights=[MetricInsightResponse.model_validate(item.model_dump()) for item in data.insights],
        alerts=[HealthAlertResponse.model_validate(item.model_dump()) for item in data.alerts],
        recommendations=[
            HealthRecommendationResponse.model_validate(item.model_dump())
            for item in data.recommendations
        ],
        disclaimer=data.disclaimer,
    )


@router.get(
    "/insights",
    response_model=HealthMeasurementInsightsResponse,
    summary="Get health measurement clinical insights",
)
async def get_health_measurement_insights(
    request: Request,
    current_user: ClinicalUser,
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    patient_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HealthMeasurementInsightsResponse:
    """Return rule-based clinical insights and health alerts for one owned patient."""
    insights = await audit_analytics_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        analytics_endpoint="insights",
        patient_id=patient_id,
        policy_service=analytics_service,
        date_from=date_from,
        date_to=date_to,
        period=None,
        load=lambda: analytics_service.get_insights(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return _insights_response(insights)
