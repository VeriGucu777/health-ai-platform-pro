"""Stroke risk assessment API response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.diabetes_risk_assessment import (
    ContributingFactorResponse,
    MissingInputResponse,
)
from app.api.schemas.health_measurement_insights import HealthRecommendationResponse
from app.core.reference_ranges import STROKE_RISK_DISCLAIMER

AssessmentStatus = Literal["completed", "insufficient_data"]
RiskLevel = Literal["low", "moderate", "elevated"]


class StrokeRiskAssessmentResponse(BaseModel):
    """Informational stroke risk assessment for one owned patient."""

    patient_id: UUID
    date_from: datetime
    date_to: datetime
    model_version: str
    assessment_status: AssessmentStatus
    risk_level: RiskLevel | None = None
    score: float | None = None
    probability: float | None = None
    contributing_factors: list[ContributingFactorResponse]
    missing_inputs: list[MissingInputResponse]
    recommendations: list[HealthRecommendationResponse]
    disclaimer: str = Field(
        default=STROKE_RISK_DISCLAIMER,
        description=(
            "Mandatory informational disclaimer. This assessment is not a diagnosis and does not "
            "replace evaluation by a qualified healthcare professional."
        ),
    )

    model_config = ConfigDict(from_attributes=True)
