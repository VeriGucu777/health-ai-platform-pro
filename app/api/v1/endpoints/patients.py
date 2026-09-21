"""Patient CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicalUser, get_audit_service, get_patient_service
from app.api.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.application.dtos.patient import PatientDTO, PatientListDTO
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.patient_audit_recorder import record_patient_audit_event
from app.application.services.patient_service import PatientService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

router = APIRouter()


def _patient_response(patient: PatientDTO) -> PatientResponse:
    return PatientResponse.model_validate(patient.model_dump())


def _patient_list_response(data: PatientListDTO) -> PatientListResponse:
    return PatientListResponse(
        items=[_patient_response(item) for item in data.items],
        total=data.total,
        page=data.page,
        page_size=data.page_size,
        pages=data.pages,
    )


async def _audit_patient_failure(
    *,
    audit_service: AuditService,
    audit_context,
    current_user: UserDTO,
    action: AuditAction,
    resource_id: UUID | None,
    exc: AppException,
) -> None:
    await record_patient_audit_event(
        audit_service,
        action=action,
        outcome=AuditOutcome.FAILURE,
        http_status=exc.status_code,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=resource_id,
    )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient",
)
async def create_patient(
    body: PatientCreate,
    request: Request,
    current_user: ClinicalUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientResponse:
    """Create a patient owned by the authenticated user."""
    audit_context = build_auth_audit_context(request)
    try:
        patient, organization_id = await patient_service.create_patient_for_user(
            current_user.id,
            current_user.role,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            gender=body.gender,
            phone=body.phone,
            notes=body.notes,
            is_active=body.is_active,
        )
    except AppException as exc:
        await _audit_patient_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.CREATE,
            resource_id=None,
            exc=exc,
        )
        raise

    await record_patient_audit_event(
        audit_service,
        action=AuditAction.CREATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_201_CREATED,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=patient.id,
        organization_id=organization_id,
    )
    return _patient_response(patient)


@router.get(
    "",
    response_model=PatientListResponse,
    summary="List patients",
)
async def list_patients(
    request: Request,
    current_user: ClinicalUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PatientListResponse:
    """List patients belonging to the authenticated user."""
    audit_context = build_auth_audit_context(request)
    metadata = {"page": page, "page_size": page_size}
    try:
        patients = await patient_service.list_patients_for_user(
            current_user.id,
            current_user.role,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        await record_patient_audit_event(
            audit_service,
            action=AuditAction.LIST,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            resource_id=None,
            metadata=metadata,
        )
        raise

    await record_patient_audit_event(
        audit_service,
        action=AuditAction.LIST,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=None,
        metadata=metadata,
    )
    return _patient_list_response(patients)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient",
)
async def get_patient(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientResponse:
    """Retrieve a single patient owned by the authenticated user."""
    audit_context = build_auth_audit_context(request)
    try:
        patient = await patient_service.get_patient_for_user(
            current_user.id,
            current_user.role,
            patient_id,
        )
    except AppException as exc:
        await _audit_patient_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.VIEW,
            resource_id=patient_id,
            exc=exc,
        )
        raise

    await record_patient_audit_event(
        audit_service,
        action=AuditAction.VIEW,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=patient_id,
    )
    return _patient_response(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient",
)
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    request: Request,
    current_user: ClinicalUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientResponse:
    """Update a patient owned by the authenticated user."""
    audit_context = build_auth_audit_context(request)
    try:
        patient, organization_id = await patient_service.update_patient_for_user(
            current_user.id,
            current_user.role,
            patient_id,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            gender=body.gender,
            phone=body.phone,
            notes=body.notes,
        )
    except AppException as exc:
        await _audit_patient_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.UPDATE,
            resource_id=patient_id,
            exc=exc,
        )
        raise

    await record_patient_audit_event(
        audit_service,
        action=AuditAction.UPDATE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=patient_id,
        organization_id=organization_id,
    )
    return _patient_response(patient)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient",
)
async def delete_patient(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> None:
    """Delete a patient owned by the authenticated user."""
    audit_context = build_auth_audit_context(request)
    try:
        organization_id = await patient_service.delete_patient_for_user(
            current_user.id,
            current_user.role,
            patient_id,
        )
    except AppException as exc:
        await _audit_patient_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.DELETE,
            resource_id=patient_id,
            exc=exc,
        )
        raise

    await record_patient_audit_event(
        audit_service,
        action=AuditAction.DELETE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_204_NO_CONTENT,
        audit_context=audit_context,
        current_user=current_user,
        resource_id=patient_id,
        organization_id=organization_id,
    )
