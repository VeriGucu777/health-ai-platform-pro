"""Clinic admin patient assignment management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicAdminUser, get_audit_service, get_clinic_admin_organization_service
from app.api.schemas.clinic_admin_organization import (
    PatientAssignmentCreate,
    PatientAssignmentListResponse,
    PatientAssignmentResponse,
)
from app.application.dtos.clinic_admin_organization import PatientAssignmentDTO, PatientAssignmentListDTO
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinic_admin_organization_service import (
    ClinicAdminOrganizationService,
)
from app.application.services.patient_assignment_audit_recorder import (
    record_patient_assignment_audit_event,
)
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

router = APIRouter()


def _assignment_response(data: PatientAssignmentDTO) -> PatientAssignmentResponse:
    return PatientAssignmentResponse.model_validate(data.model_dump())


def _assignment_list_response(data: PatientAssignmentListDTO) -> PatientAssignmentListResponse:
    return PatientAssignmentListResponse(
        items=[_assignment_response(item) for item in data.items],
    )


async def _audit_failure(
    *,
    audit_service: AuditService,
    audit_context,
    current_user: UserDTO,
    action: AuditAction,
    patient_id: UUID,
    exc: AppException,
) -> None:
    await record_patient_assignment_audit_event(
        audit_service,
        action=action,
        outcome=AuditOutcome.FAILURE,
        http_status=exc.status_code,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
    )


@router.get(
    "/{patient_id}/assignments",
    response_model=PatientAssignmentListResponse,
    summary="List patient assignments in the clinic admin organization",
)
async def list_patient_assignments(
    patient_id: UUID,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[ClinicAdminOrganizationService, Depends(get_clinic_admin_organization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientAssignmentListResponse:
    audit_context = build_auth_audit_context(request)
    try:
        assignments = await service.list_patient_assignments(current_user.id, patient_id)
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.LIST,
            patient_id=patient_id,
            exc=exc,
        )
        raise

    await record_patient_assignment_audit_event(
        audit_service,
        action=AuditAction.LIST,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        organization_id=assignments.organization_id,
    )
    return _assignment_list_response(assignments)


@router.post(
    "/{patient_id}/assignments",
    response_model=PatientAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a doctor assignment for a patient",
)
async def create_patient_assignment(
    patient_id: UUID,
    body: PatientAssignmentCreate,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[ClinicAdminOrganizationService, Depends(get_clinic_admin_organization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientAssignmentResponse:
    audit_context = build_auth_audit_context(request)
    metadata = {"is_primary": body.is_primary}
    try:
        assignment = await service.create_patient_assignment(
            current_user.id,
            patient_id,
            assignee_user_id=body.assignee_user_id,
            is_primary=body.is_primary,
        )
    except AppException as exc:
        await record_patient_assignment_audit_event(
            audit_service,
            action=AuditAction.CREATE,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            metadata=metadata,
        )
        raise

    await record_patient_assignment_audit_event(
        audit_service,
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_201_CREATED,
        audit_context=audit_context,
        current_user=current_user,
        assignment_id=assignment.id,
        patient_id=patient_id,
        organization_id=assignment.organization_id,
        metadata=metadata,
    )
    return _assignment_response(assignment)


@router.patch(
    "/{patient_id}/assignments/{assignment_id}",
    response_model=PatientAssignmentResponse,
    summary="Deactivate a patient assignment",
)
async def deactivate_patient_assignment(
    patient_id: UUID,
    assignment_id: UUID,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[ClinicAdminOrganizationService, Depends(get_clinic_admin_organization_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientAssignmentResponse:
    audit_context = build_auth_audit_context(request)
    try:
        assignment = await service.deactivate_patient_assignment(
            current_user.id,
            patient_id,
            assignment_id,
        )
    except AppException as exc:
        await record_patient_assignment_audit_event(
            audit_service,
            action=AuditAction.DEACTIVATE,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            assignment_id=assignment_id,
            patient_id=patient_id,
        )
        raise

    await record_patient_assignment_audit_event(
        audit_service,
        action=AuditAction.DEACTIVATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        assignment_id=assignment.id,
        patient_id=patient_id,
        organization_id=assignment.organization_id,
    )
    return _assignment_response(assignment)
