"""Risk assessment history read endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import ClinicalUser, get_audit_service, get_risk_assessment_history_service
from app.api.risk_assessment_history_read_audit import audit_risk_history_list
from app.api.schemas.risk_assessment_history import (
    RiskAssessmentHistoryListResponse,
    RiskAssessmentHistoryResponse,
)
from app.application.dtos.risk_assessment_history import RiskAssessmentHistoryListDTO
from app.application.services.audit_service import AuditService
from app.application.services.risk_assessment_history_service import RiskAssessmentHistoryService
from app.domain.risk.enums import RiskAssessmentType

router = APIRouter()


def _list_response(data: RiskAssessmentHistoryListDTO) -> RiskAssessmentHistoryListResponse:
    return RiskAssessmentHistoryListResponse(
        items=[RiskAssessmentHistoryResponse.model_validate(item.model_dump()) for item in data.items],
        total=data.total,
        page=data.page,
        page_size=data.page_size,
        pages=data.pages,
    )


@router.get(
    "/{patient_id}/risk-assessments/history",
    response_model=RiskAssessmentHistoryListResponse,
    summary="List immutable risk assessment history for a patient",
)
async def list_risk_assessment_history(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    history_service: Annotated[
        RiskAssessmentHistoryService,
        Depends(get_risk_assessment_history_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    assessment_type: RiskAssessmentType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> RiskAssessmentHistoryListResponse:
    """Return newest-first immutable snapshots (READ policy)."""
    type_str = assessment_type.value if assessment_type else None

    async def load():
        return await history_service.list_history_for_user(
            current_user.id,
            current_user.role,
            patient_id,
            assessment_type=assessment_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

    data = await audit_risk_history_list(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        patient_id=patient_id,
        organization_id=None,
        assessment_type=type_str,
        page=page,
        page_size=page_size,
        load=load,
    )
    return _list_response(data)
