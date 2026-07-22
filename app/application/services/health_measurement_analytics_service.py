"""Health measurement analytics application service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.application.analytics.health_measurement_analytics import (
    AnalyticsPeriod,
    bucket_measurements,
    compute_metric_statistics,
    metrics_to_include,
)
from app.application.analytics.health_measurement_insights import build_insights
from app.application.dtos.health_measurement_analytics import (
    HealthMeasurementSummaryDTO,
    HealthMeasurementTrendsDTO,
    MetricStatisticsDTO,
    PeriodSummaryDTO,
)
from app.application.dtos.health_measurement_insights import (
    HealthAlertDTO,
    HealthMeasurementInsightsDTO,
    HealthRecommendationDTO,
    MetricInsightDTO,
)
from app.application.services.base import BaseService
from app.core.exceptions import NotFoundError, ValidationError
from app.core.reference_ranges import MAX_ANALYTICS_DATE_RANGE_DAYS, TRACKABLE_METRICS
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.patient_repository import PatientRepository


class HealthMeasurementAnalyticsService(BaseService):
    """Read-only analytics for health measurements scoped to one owned patient."""

    def __init__(
        self,
        health_measurement_repository: HealthMeasurementRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._health_measurements = health_measurement_repository
        self._patients = patient_repository

    async def get_summary(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        metric: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> HealthMeasurementSummaryDTO:
        measurements, resolved_from, resolved_to = await self._load_measurements(
            owner_id,
            patient_id=patient_id,
            metric=metric,
            date_from=date_from,
            date_to=date_to,
        )
        overall = self._build_metric_statistics(measurements, metric)
        return HealthMeasurementSummaryDTO(
            patient_id=patient_id,
            metric=metric,
            date_from=resolved_from,
            date_to=resolved_to,
            total_measurement_count=len(measurements),
            overall=overall,
        )

    async def get_trends(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        period: AnalyticsPeriod,
        metric: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> HealthMeasurementTrendsDTO:
        measurements, resolved_from, resolved_to = await self._load_measurements(
            owner_id,
            patient_id=patient_id,
            metric=metric,
            date_from=date_from,
            date_to=date_to,
        )
        overall = self._build_metric_statistics(measurements, metric)
        period_summaries = [
            PeriodSummaryDTO(
                period_start=period_start,
                period_end=period_end,
                measurement_count=len(bucket_items),
                metrics=self._build_metric_statistics(bucket_items, metric),
            )
            for period_start, period_end, bucket_items in bucket_measurements(
                measurements,
                period,
            )
        ]
        return HealthMeasurementTrendsDTO(
            patient_id=patient_id,
            metric=metric,
            date_from=resolved_from,
            date_to=resolved_to,
            period=period,
            total_measurement_count=len(measurements),
            overall=overall,
            periods=period_summaries,
        )

    async def get_insights(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> HealthMeasurementInsightsDTO:
        measurements, resolved_from, resolved_to = await self._load_measurements(
            owner_id,
            patient_id=patient_id,
            metric=None,
            date_from=date_from,
            date_to=date_to,
        )
        insight_payload = build_insights(measurements)
        return HealthMeasurementInsightsDTO(
            patient_id=patient_id,
            date_from=resolved_from,
            date_to=resolved_to,
            overall_status=str(insight_payload["overall_status"]),
            insights=[MetricInsightDTO(**item) for item in insight_payload["insights"]],
            alerts=[HealthAlertDTO(**item) for item in insight_payload["alerts"]],
            recommendations=[
                HealthRecommendationDTO(**item) for item in insight_payload["recommendations"]
            ],
        )

    async def _load_measurements(
        self,
        owner_id: UUID,
        *,
        patient_id: UUID,
        metric: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[list, datetime, datetime]:
        await self._validate_patient_ownership(owner_id, patient_id)
        self._validate_metric(metric)

        resolved_to = date_to or datetime.now(UTC)
        resolved_from = date_from or (resolved_to - timedelta(days=30))

        self._validate_date_range(resolved_from, resolved_to)

        measurements = await self._health_measurements.list_by_owner_for_analytics(
            owner_id,
            patient_id=patient_id,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        return measurements, resolved_from, resolved_to

    def _build_metric_statistics(
        self,
        measurements: list,
        metric_filter: str | None,
    ) -> list[MetricStatisticsDTO]:
        return [
            MetricStatisticsDTO(**compute_metric_statistics(measurements, metric))
            for metric in metrics_to_include(metric_filter)
        ]

    async def _validate_patient_ownership(self, owner_id: UUID, patient_id: UUID) -> None:
        patient = await self._patients.get_by_id_and_owner(patient_id, owner_id)
        if patient is None:
            raise NotFoundError("Patient not found")

    def _validate_metric(self, metric: str | None) -> None:
        if metric is not None and metric not in TRACKABLE_METRICS:
            raise ValidationError(f"metric must be one of: {', '.join(TRACKABLE_METRICS)}")

    def _validate_date_range(self, date_from: datetime, date_to: datetime) -> None:
        if date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")

        if (date_to - date_from).days > MAX_ANALYTICS_DATE_RANGE_DAYS:
            raise ValidationError("Date range cannot exceed 366 days")
