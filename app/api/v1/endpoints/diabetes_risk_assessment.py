"""Diabetes risk assessment endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_diabetes_risk_assessment_service
from app.api.schemas.diabetes_risk_assessment import (
    ContributingFactorResponse,
    DiabetesRiskAssessmentResponse,
    MissingInputResponse,
)
from app.api.schemas.health_measurement_insights import HealthRecommendationResponse
from app.application.dtos.diabetes_risk_assessment import DiabetesRiskAssessmentDTO
from app.application.services.diabetes_risk_assessment_service import DiabetesRiskAssessmentService

router = APIRouter()


def _assessment_response(data: DiabetesRiskAssessmentDTO) -> DiabetesRiskAssessmentResponse:
    return DiabetesRiskAssessmentResponse(
        patient_id=data.patient_id,
        date_from=data.date_from,
        date_to=data.date_to,
        model_version=data.model_version,
        assessment_status=data.assessment_status,
        risk_level=data.risk_level,
        score=data.score,
        probability=data.probability,
        contributing_factors=[
            ContributingFactorResponse.model_validate(item.model_dump())
            for item in data.contributing_factors
        ],
        missing_inputs=[
            MissingInputResponse.model_validate(item.model_dump())
            for item in data.missing_inputs
        ],
        recommendations=[
            HealthRecommendationResponse.model_validate(item.model_dump())
            for item in data.recommendations
        ],
        disclaimer=data.disclaimer,
    )


@router.get(
    "/{patient_id}/risk-assessments/diabetes",
    response_model=DiabetesRiskAssessmentResponse,
    summary="Assess informational diabetes risk for one owned patient",
)
async def assess_diabetes_risk(
    patient_id: UUID,
    current_user: CurrentUser,
    assessment_service: Annotated[
        DiabetesRiskAssessmentService,
        Depends(get_diabetes_risk_assessment_service),
    ],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DiabetesRiskAssessmentResponse:
    """Return an on-demand, non-diagnostic diabetes risk assessment from recorded patient data."""
    assessment = await assessment_service.assess_diabetes_risk(
        current_user.id,
        patient_id=patient_id,
        date_from=date_from,
        date_to=date_to,
    )
    return _assessment_response(assessment)
