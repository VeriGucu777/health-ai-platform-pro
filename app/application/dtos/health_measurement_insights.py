"""Health measurement insights application DTOs."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.core.reference_ranges import INSIGHTS_DISCLAIMER


class MetricInsightDTO(BaseSchema):
    """Rule-based insight for one trackable metric."""

    metric: str
    status: str
    severity: str
    latest_value: Decimal | None = None
    average_value: Decimal | None = None
    trend_direction: str
    message: str


class HealthAlertDTO(BaseSchema):
    """High-priority alert derived from an insight."""

    metric: str
    severity: str
    message: str


class HealthRecommendationDTO(BaseSchema):
    """Non-prescriptive tracking recommendation."""

    category: str
    message: str
    related_metrics: list[str]


class HealthMeasurementInsightsDTO(BaseSchema):
    """Clinical insights and health alerts for one patient."""

    patient_id: UUID
    date_from: datetime
    date_to: datetime
    overall_status: str
    insights: list[MetricInsightDTO]
    alerts: list[HealthAlertDTO]
    recommendations: list[HealthRecommendationDTO]
    disclaimer: str = INSIGHTS_DISCLAIMER
