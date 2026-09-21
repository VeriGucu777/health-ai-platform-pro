"""Medical record CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.clinical_child_read_audit import audit_child_list, audit_child_view
from app.api.deps import ClinicalUser, get_audit_service, get_medical_record_service
from app.api.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.application.dtos.medical_record import MedicalRecordDTO, MedicalRecordListDTO
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_child_audit_recorder import record_clinical_child_audit_event
from app.application.services.medical_record_service import MedicalRecordService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

router = APIRouter()


def _medical_record_response(medical_record: MedicalRecordDTO) -> MedicalRecordResponse:
    return MedicalRecordResponse.model_validate(medical_record.model_dump())


def _medical_record_list_response(data: MedicalRecordListDTO) -> MedicalRecordListResponse:
    return MedicalRecordListResponse(
        items=[_medical_record_response(item) for item in data.items],
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
        child_kind="medical_record",
        patient_id=patient_id,
        child_id=child_id,
    )


@router.post(
    "",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create medical record",
)
async def create_medical_record(
    body: MedicalRecordCreate,
    request: Request,
    current_user: ClinicalUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> MedicalRecordResponse:
    """Create a medical record for an accessible patient."""
    audit_context = build_auth_audit_context(request)
    try:
        medical_record, organization_id = await medical_record_service.create_medical_record(
            current_user.id,
            current_user.role,
            patient_id=body.patient_id,
            record_date=body.record_date,
            record_type=body.record_type,
            title=body.title,
            description=body.description,
            diagnosis=body.diagnosis,
            treatment=body.treatment,
            medications=body.medications,
            doctor_name=body.doctor_name,
            hospital_name=body.hospital_name,
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
        child_kind="medical_record",
        patient_id=medical_record.patient_id,
        child_id=medical_record.id,
        organization_id=organization_id,
    )
    return _medical_record_response(medical_record)


@router.get(
    "",
    response_model=MedicalRecordListResponse,
    summary="List medical records",
)
async def list_medical_records(
    request: Request,
    current_user: ClinicalUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
    record_type: str | None = None,
) -> MedicalRecordListResponse:
    """List medical records for patients the caller may access."""
    medical_records = await audit_child_list(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="medical_record",
        patient_id=patient_id,
        page=page,
        page_size=page_size,
        policy_service=medical_record_service,
        load=lambda: medical_record_service.list_medical_records(
            current_user.id,
            current_user.role,
            page=page,
            page_size=page_size,
            patient_id=patient_id,
            record_type=record_type,
        ),
    )
    return _medical_record_list_response(medical_records)


@router.get(
    "/{medical_record_id}",
    response_model=MedicalRecordResponse,
    summary="Get medical record",
)
async def get_medical_record(
    medical_record_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> MedicalRecordResponse:
    """Retrieve a single medical record when the linked patient is accessible."""

    async def _load() -> tuple[MedicalRecordDTO, UUID | None, UUID]:
        medical_record, organization_id = await medical_record_service.get_medical_record(
            current_user.id,
            current_user.role,
            medical_record_id,
        )
        return medical_record, organization_id, medical_record.patient_id

    medical_record = await audit_child_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="medical_record",
        child_id=medical_record_id,
        load=_load,
    )
    return _medical_record_response(medical_record)


@router.patch(
    "/{medical_record_id}",
    response_model=MedicalRecordResponse,
    summary="Update medical record",
)
async def update_medical_record(
    medical_record_id: UUID,
    body: MedicalRecordUpdate,
    request: Request,
    current_user: ClinicalUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> MedicalRecordResponse:
    """Update a medical record when the linked patient is writable."""
    audit_context = build_auth_audit_context(request)
    try:
        medical_record, organization_id = await medical_record_service.update_medical_record(
            current_user.id,
            current_user.role,
            medical_record_id,
            record_date=body.record_date,
            record_type=body.record_type,
            title=body.title,
            description=body.description,
            diagnosis=body.diagnosis,
            treatment=body.treatment,
            medications=body.medications,
            doctor_name=body.doctor_name,
            hospital_name=body.hospital_name,
            notes=body.notes,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.UPDATE,
            patient_id=None,
            child_id=medical_record_id,
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
        child_kind="medical_record",
        patient_id=medical_record.patient_id,
        child_id=medical_record.id,
        organization_id=organization_id,
    )
    return _medical_record_response(medical_record)


@router.delete(
    "/{medical_record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete medical record",
)
async def delete_medical_record(
    medical_record_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> None:
    """Delete a medical record when the linked patient is deletable."""
    audit_context = build_auth_audit_context(request)
    patient_id: UUID | None = None
    try:
        organization_id, patient_id = await medical_record_service.delete_medical_record(
            current_user.id,
            current_user.role,
            medical_record_id,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.DELETE,
            patient_id=patient_id,
            child_id=medical_record_id,
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
        child_kind="medical_record",
        patient_id=patient_id,
        child_id=medical_record_id,
        organization_id=organization_id,
    )
