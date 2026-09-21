"""Appointment CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.clinical_child_read_audit import audit_child_list, audit_child_view
from app.api.deps import ClinicalUser, get_appointment_service, get_audit_service
from app.api.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.application.dtos.appointment import AppointmentDTO, AppointmentListDTO
from app.application.dtos.user import UserDTO
from app.application.services.appointment_service import AppointmentService
from app.application.services.audit_service import AuditService
from app.application.services.clinical_child_audit_recorder import record_clinical_child_audit_event
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

router = APIRouter()


def _appointment_response(appointment: AppointmentDTO) -> AppointmentResponse:
    return AppointmentResponse.model_validate(appointment.model_dump())


def _appointment_list_response(data: AppointmentListDTO) -> AppointmentListResponse:
    return AppointmentListResponse(
        items=[_appointment_response(item) for item in data.items],
        total=data.total,
        page=data.page,
        page_size=data.page_size,
        pages=data.pages,
    )


async def _audit_failure(
    *,
    audit_service: AuditService,
    audit_context,
    current_user: UserDTO,
    action: AuditAction,
    patient_id: UUID | None,
    child_id: UUID | None,
    exc: AppException,
) -> None:
    await record_clinical_child_audit_event(
        audit_service,
        action=action,
        outcome=AuditOutcome.FAILURE,
        http_status=exc.status_code,
        audit_context=audit_context,
        current_user=current_user,
        child_kind="appointment",
        patient_id=patient_id,
        child_id=child_id,
    )


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create appointment",
)
async def create_appointment(
    body: AppointmentCreate,
    request: Request,
    current_user: ClinicalUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AppointmentResponse:
    """Create an appointment for an accessible patient."""
    audit_context = build_auth_audit_context(request)
    try:
        appointment, organization_id = await appointment_service.create_appointment(
            current_user.id,
            current_user.role,
            patient_id=body.patient_id,
            appointment_date=body.appointment_date,
            appointment_type=body.appointment_type,
            status=body.status,
            notes=body.notes,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.CREATE,
            patient_id=body.patient_id,
            child_id=None,
            exc=exc,
        )
        raise

    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_201_CREATED,
        audit_context=audit_context,
        current_user=current_user,
        child_kind="appointment",
        patient_id=appointment.patient_id,
        child_id=appointment.id,
        organization_id=organization_id,
    )
    return _appointment_response(appointment)


@router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List appointments",
)
async def list_appointments(
    request: Request,
    current_user: ClinicalUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
) -> AppointmentListResponse:
    """List appointments for patients the caller may access."""
    appointments = await audit_child_list(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="appointment",
        patient_id=patient_id,
        page=page,
        page_size=page_size,
        policy_service=appointment_service,
        load=lambda: appointment_service.list_appointments(
            current_user.id,
            current_user.role,
            page=page,
            page_size=page_size,
            patient_id=patient_id,
        ),
    )
    return _appointment_list_response(appointments)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get appointment",
)
async def get_appointment(
    appointment_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AppointmentResponse:
    """Retrieve a single appointment when the linked patient is accessible."""

    async def _load() -> tuple[AppointmentDTO, UUID | None, UUID]:
        appointment, organization_id = await appointment_service.get_appointment(
            current_user.id,
            current_user.role,
            appointment_id,
        )
        return appointment, organization_id, appointment.patient_id

    appointment = await audit_child_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="appointment",
        child_id=appointment_id,
        load=_load,
    )
    return _appointment_response(appointment)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update appointment",
)
async def update_appointment(
    appointment_id: UUID,
    body: AppointmentUpdate,
    request: Request,
    current_user: ClinicalUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> AppointmentResponse:
    """Update an appointment when the linked patient is writable."""
    audit_context = build_auth_audit_context(request)
    try:
        appointment, organization_id = await appointment_service.update_appointment(
            current_user.id,
            current_user.role,
            appointment_id,
            patient_id=body.patient_id,
            appointment_date=body.appointment_date,
            appointment_type=body.appointment_type,
            status=body.status,
            notes=body.notes,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.UPDATE,
            patient_id=body.patient_id,
            child_id=appointment_id,
            exc=exc,
        )
        raise

    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.UPDATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        child_kind="appointment",
        patient_id=appointment.patient_id,
        child_id=appointment.id,
        organization_id=organization_id,
    )
    return _appointment_response(appointment)


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appointment",
)
async def delete_appointment(
    appointment_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> None:
    """Delete an appointment when the linked patient is deletable."""
    audit_context = build_auth_audit_context(request)
    patient_id: UUID | None = None
    try:
        organization_id, patient_id = await appointment_service.delete_appointment(
            current_user.id,
            current_user.role,
            appointment_id,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.DELETE,
            patient_id=patient_id,
            child_id=appointment_id,
            exc=exc,
        )
        raise

    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.DELETE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_204_NO_CONTENT,
        audit_context=audit_context,
        current_user=current_user,
        child_kind="appointment",
        patient_id=patient_id,
        child_id=appointment_id,
        organization_id=organization_id,
    )
