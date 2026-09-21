"""Patient clinical timeline endpoints."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicalUser, get_audit_service, get_patient_clinical_timeline_service
from app.api.schemas.patient_clinical_timeline import PatientClinicalTimelineResponse
from app.application.dtos.patient_clinical_timeline import PatientClinicalTimelineDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_timeline_audit_recorder import (
    record_clinical_timeline_audit_event,
)
from app.application.services.patient_clinical_timeline_service import (
    DEFAULT_MAX_EVENTS,
    MAX_EVENTS_CAP,
    PatientClinicalTimelineService,
)
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome

router = APIRouter()


def _timeline_response(data: PatientClinicalTimelineDTO) -> PatientClinicalTimelineResponse:
    return PatientClinicalTimelineResponse.model_validate(data.model_dump())


def _timeline_audit_metadata(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    include_risk_snapshot: bool,
) -> dict[str, Any] | None:
    metadata: dict[str, Any] = {"include_risk_snapshot": include_risk_snapshot}
    if date_from is not None:
        metadata["date_from"] = date_from.isoformat()
    if date_to is not None:
        metadata["date_to"] = date_to.isoformat()
    return metadata


@router.get(
    "/{patient_id}/clinical-timeline",
    response_model=PatientClinicalTimelineResponse,
    summary="Get patient clinical timeline",
)
async def get_patient_clinical_timeline(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    timeline_service: Annotated[
        PatientClinicalTimelineService,
        Depends(get_patient_clinical_timeline_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    max_events: Annotated[int, Query(ge=1, le=MAX_EVENTS_CAP)] = DEFAULT_MAX_EVENTS,
    include_risk_snapshot: bool = False,
) -> PatientClinicalTimelineResponse:
    """Return a read-only chronological timeline for one owned patient."""
    audit_context = build_auth_audit_context(request)
    metadata = _timeline_audit_metadata(
        date_from=date_from,
        date_to=date_to,
        include_risk_snapshot=include_risk_snapshot,
    )
    try:
        timeline, organization_id = await timeline_service.get_clinical_timeline(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            max_events=max_events,
            include_risk_snapshot=include_risk_snapshot,
        )
    except AppException as exc:
        await record_clinical_timeline_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            metadata=metadata,
        )
        raise

    await record_clinical_timeline_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        metadata=metadata,
        organization_id=organization_id,
    )
    return _timeline_response(timeline)
