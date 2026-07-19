"""Patient CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_patient_service
from app.api.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.application.dtos.patient import PatientDTO, PatientListDTO
from app.application.services.patient_service import PatientService

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


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient",
)
async def create_patient(
    body: PatientCreate,
    current_user: CurrentUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Create a patient owned by the authenticated user."""
    patient = await patient_service.create_patient(
        current_user.id,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        phone=body.phone,
        notes=body.notes,
        is_active=body.is_active,
    )
    return _patient_response(patient)


@router.get(
    "",
    response_model=PatientListResponse,
    summary="List patients",
)
async def list_patients(
    current_user: CurrentUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PatientListResponse:
    """List patients belonging to the authenticated user."""
    patients = await patient_service.list_patients(
        current_user.id,
        page=page,
        page_size=page_size,
    )
    return _patient_list_response(patients)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient",
)
async def get_patient(
    patient_id: UUID,
    current_user: CurrentUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Retrieve a single patient owned by the authenticated user."""
    patient = await patient_service.get_patient(current_user.id, patient_id)
    return _patient_response(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient",
)
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    current_user: CurrentUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientResponse:
    """Update a patient owned by the authenticated user."""
    patient = await patient_service.update_patient(
        current_user.id,
        patient_id,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        phone=body.phone,
        notes=body.notes,
        is_active=body.is_active,
    )
    return _patient_response(patient)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient",
)
async def delete_patient(
    patient_id: UUID,
    current_user: CurrentUser,
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
) -> None:
    """Delete a patient owned by the authenticated user."""
    await patient_service.delete_patient(current_user.id, patient_id)
