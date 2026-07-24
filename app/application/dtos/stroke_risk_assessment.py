"""Stroke risk assessment application DTOs."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.application.dtos.health_measurement_insights import HealthRecommendationDTO
from app.application.dtos.risk_assessment_shared import (
    ContributingFactorDTO,
    MissingInputDTO,
)
from app.core.reference_ranges import STROKE_RISK_DISCLAIMER

__all__ = [
    "ContributingFactorDTO",
    "MissingInputDTO",
    "StrokeRiskAssessmentDTO",
]


class StrokeRiskAssessmentDTO(BaseSchema):
    """On-demand stroke risk assessment for one owned patient."""

    patient_id: UUID
    date_from: datetime
    date_to: datetime
    model_version: str
    assessment_status: str
    risk_level: str | None = None
    score: float | None = None
    probability: float | None = None
    contributing_factors: list[ContributingFactorDTO]
    missing_inputs: list[MissingInputDTO]
    recommendations: list[HealthRecommendationDTO]
    disclaimer: str = STROKE_RISK_DISCLAIMER
