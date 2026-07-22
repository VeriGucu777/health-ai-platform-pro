"""Medical record CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_medical_record_service
from app.api.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.application.dtos.medical_record import MedicalRecordDTO, MedicalRecordListDTO
from app.application.services.medical_record_service import MedicalRecordService

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


@router.post(
    "",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create medical record",
)
async def create_medical_record(
    body: MedicalRecordCreate,
    current_user: CurrentUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
) -> MedicalRecordResponse:
    """Create a medical record for a patient owned by the authenticated user."""
    medical_record = await medical_record_service.create_medical_record(
        current_user.id,
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
    return _medical_record_response(medical_record)


@router.get(
    "",
    response_model=MedicalRecordListResponse,
    summary="List medical records",
)
async def list_medical_records(
    current_user: CurrentUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
    record_type: str | None = None,
) -> MedicalRecordListResponse:
    """List medical records belonging to the authenticated user."""
    medical_records = await medical_record_service.list_medical_records(
        current_user.id,
        page=page,
        page_size=page_size,
        patient_id=patient_id,
        record_type=record_type,
    )
    return _medical_record_list_response(medical_records)


@router.get(
    "/{medical_record_id}",
    response_model=MedicalRecordResponse,
    summary="Get medical record",
)
async def get_medical_record(
    medical_record_id: UUID,
    current_user: CurrentUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
) -> MedicalRecordResponse:
    """Retrieve a single medical record owned by the authenticated user."""
    medical_record = await medical_record_service.get_medical_record(
        current_user.id,
        medical_record_id,
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
    current_user: CurrentUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
) -> MedicalRecordResponse:
    """Update a medical record owned by the authenticated user."""
    medical_record = await medical_record_service.update_medical_record(
        current_user.id,
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
    return _medical_record_response(medical_record)


@router.delete(
    "/{medical_record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete medical record",
)
async def delete_medical_record(
    medical_record_id: UUID,
    current_user: CurrentUser,
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
) -> None:
    """Delete a medical record owned by the authenticated user."""
    await medical_record_service.delete_medical_record(current_user.id, medical_record_id)
