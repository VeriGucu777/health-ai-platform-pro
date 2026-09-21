"""Patient clinical summary endpoints."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicalUser, get_audit_service, get_patient_clinical_summary_service
from app.api.schemas.patient_clinical_summary import PatientClinicalSummaryResponse
from app.application.clinical_summary.constants import SUMMARY_VERSION
from app.application.dtos.patient_clinical_summary import PatientClinicalSummaryDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_summary_audit_recorder import (
    record_clinical_summary_audit_event,
)
from app.application.services.patient_clinical_summary_service import PatientClinicalSummaryService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome

router = APIRouter()


def _summary_response(data: PatientClinicalSummaryDTO) -> PatientClinicalSummaryResponse:
    return PatientClinicalSummaryResponse.model_validate(data.model_dump())


def _summary_audit_metadata(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict[str, Any] | None:
    metadata: dict[str, Any] = {"summary_version": SUMMARY_VERSION}
    if date_from is not None:
        metadata["date_from"] = date_from.isoformat()
    if date_to is not None:
        metadata["date_to"] = date_to.isoformat()
    return metadata


@router.get(
    "/{patient_id}/clinical-summary",
    response_model=PatientClinicalSummaryResponse,
    summary="Get deterministic patient clinical summary",
)
async def get_patient_clinical_summary(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    summary_service: Annotated[
        PatientClinicalSummaryService,
        Depends(get_patient_clinical_summary_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PatientClinicalSummaryResponse:
    """Return a structured deterministic summary from authorized clinical evidence."""
    audit_context = build_auth_audit_context(request)
    metadata = _summary_audit_metadata(date_from=date_from, date_to=date_to)
    try:
        summary, organization_id = await summary_service.get_clinical_summary(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        )
    except AppException as exc:
        await record_clinical_summary_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            metadata=metadata,
        )
        raise

    await record_clinical_summary_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        metadata=metadata,
        organization_id=organization_id,
    )
    return _summary_response(summary)
