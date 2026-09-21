"""Heart disease risk assessment endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.deps import ClinicalUser, get_audit_service, get_heart_disease_risk_assessment_service
from app.api.risk_assessment_audit import run_risk_assessment_with_audit
from app.api.schemas.diabetes_risk_assessment import (
    ContributingFactorResponse,
    MissingInputResponse,
)
from app.api.schemas.health_measurement_insights import HealthRecommendationResponse
from app.api.schemas.heart_disease_risk_assessment import HeartDiseaseRiskAssessmentResponse
from app.application.dtos.heart_disease_risk_assessment import HeartDiseaseRiskAssessmentDTO
from app.application.services.audit_service import AuditService
from app.application.services.heart_disease_risk_assessment_service import (
    HeartDiseaseRiskAssessmentService,
)

router = APIRouter()


def _assessment_response(data: HeartDiseaseRiskAssessmentDTO) -> HeartDiseaseRiskAssessmentResponse:
    return HeartDiseaseRiskAssessmentResponse(
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
    "/{patient_id}/risk-assessments/heart-disease",
    response_model=HeartDiseaseRiskAssessmentResponse,
    summary="Assess informational heart disease risk for one owned patient",
)
async def assess_heart_disease_risk(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    assessment_service: Annotated[
        HeartDiseaseRiskAssessmentService,
        Depends(get_heart_disease_risk_assessment_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> HeartDiseaseRiskAssessmentResponse:
    """Return an on-demand, non-diagnostic heart disease risk assessment from recorded patient data."""
    assessment = await run_risk_assessment_with_audit(
        request=request,
        current_user=current_user,
        patient_id=patient_id,
        risk_kind="heart_disease",
        audit_service=audit_service,
        assess=lambda: assessment_service.assess_heart_disease_risk(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return _assessment_response(assessment)
