"""Stroke risk assessment endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.deps import ClinicalUser, get_audit_service, get_stroke_risk_assessment_service
from app.api.risk_assessment_audit import run_risk_assessment_with_audit
from app.api.schemas.diabetes_risk_assessment import (
    ContributingFactorResponse,
    MissingInputResponse,
)
from app.api.schemas.health_measurement_insights import HealthRecommendationResponse
from app.api.schemas.stroke_risk_assessment import StrokeRiskAssessmentResponse
from app.application.dtos.stroke_risk_assessment import StrokeRiskAssessmentDTO
from app.application.services.audit_service import AuditService
from app.application.services.stroke_risk_assessment_service import StrokeRiskAssessmentService

router = APIRouter()


def _assessment_response(data: StrokeRiskAssessmentDTO) -> StrokeRiskAssessmentResponse:
    return StrokeRiskAssessmentResponse(
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
    "/{patient_id}/risk-assessments/stroke",
    response_model=StrokeRiskAssessmentResponse,
    summary="Assess informational stroke risk for one owned patient",
)
async def assess_stroke_risk(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    assessment_service: Annotated[
        StrokeRiskAssessmentService,
        Depends(get_stroke_risk_assessment_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> StrokeRiskAssessmentResponse:
    """Return an on-demand, non-diagnostic stroke risk assessment from recorded patient data."""
    assessment = await run_risk_assessment_with_audit(
        request=request,
        current_user=current_user,
        patient_id=patient_id,
        risk_kind="stroke",
        audit_service=audit_service,
        assess=lambda: assessment_service.assess_stroke_risk(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return _assessment_response(assessment)
