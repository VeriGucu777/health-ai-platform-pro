"""Health measurement insights API response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.reference_ranges import INSIGHTS_DISCLAIMER

InsightSeverity = Literal["normal", "info", "warning", "urgent"]
InsightStatus = Literal[
    "within_reference_range",
    "below_reference_range",
    "above_reference_range",
    "insufficient_data",
    "context_required",
    "stable_trend",
    "increasing_trend",
    "decreasing_trend",
]
TrendDirection = Literal["increasing", "decreasing", "stable", "insufficient_data"]
RecommendationCategory = Literal["monitoring", "follow_up", "tracking"]


class MetricInsightResponse(BaseModel):
    """Rule-based insight for one trackable metric."""

    metric: str
    status: InsightStatus
    severity: InsightSeverity
    latest_value: Decimal | None = None
    average_value: Decimal | None = None
    trend_direction: TrendDirection
    message: str

    model_config = ConfigDict(from_attributes=True)


class HealthAlertResponse(BaseModel):
    """High-priority alert derived from an insight."""

    metric: str
    severity: Literal["warning", "urgent"]
    message: str

    model_config = ConfigDict(from_attributes=True)


class HealthRecommendationResponse(BaseModel):
    """Non-prescriptive tracking recommendation."""

    category: RecommendationCategory
    message: str
    related_metrics: list[str]

    model_config = ConfigDict(from_attributes=True)


class HealthMeasurementInsightsResponse(BaseModel):
    """Clinical insights and health alerts for one patient."""

    patient_id: UUID
    date_from: datetime
    date_to: datetime
    overall_status: InsightSeverity
    insights: list[MetricInsightResponse]
    alerts: list[HealthAlertResponse]
    recommendations: list[HealthRecommendationResponse]
    disclaimer: str = Field(
        default=INSIGHTS_DISCLAIMER,
        description=(
            "Mandatory informational disclaimer. Insights are not a diagnosis and do not "
            "replace evaluation by a qualified healthcare professional."
        ),
    )
