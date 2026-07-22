"""Appointment CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_appointment_service
from app.api.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.application.dtos.appointment import AppointmentDTO, AppointmentListDTO
from app.application.services.appointment_service import AppointmentService

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


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create appointment",
)
async def create_appointment(
    body: AppointmentCreate,
    current_user: CurrentUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Create an appointment for a patient owned by the authenticated user."""
    appointment = await appointment_service.create_appointment(
        current_user.id,
        patient_id=body.patient_id,
        appointment_date=body.appointment_date,
        appointment_type=body.appointment_type,
        status=body.status,
        notes=body.notes,
    )
    return _appointment_response(appointment)


@router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List appointments",
)
async def list_appointments(
    current_user: CurrentUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
) -> AppointmentListResponse:
    """List appointments belonging to the authenticated user."""
    appointments = await appointment_service.list_appointments(
        current_user.id,
        page=page,
        page_size=page_size,
        patient_id=patient_id,
    )
    return _appointment_list_response(appointments)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get appointment",
)
async def get_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Retrieve a single appointment owned by the authenticated user."""
    appointment = await appointment_service.get_appointment(current_user.id, appointment_id)
    return _appointment_response(appointment)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update appointment",
)
async def update_appointment(
    appointment_id: UUID,
    body: AppointmentUpdate,
    current_user: CurrentUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentResponse:
    """Update an appointment owned by the authenticated user."""
    appointment = await appointment_service.update_appointment(
        current_user.id,
        appointment_id,
        patient_id=body.patient_id,
        appointment_date=body.appointment_date,
        appointment_type=body.appointment_type,
        status=body.status,
        notes=body.notes,
    )
    return _appointment_response(appointment)


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appointment",
)
async def delete_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    appointment_service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> None:
    """Delete an appointment owned by the authenticated user."""
    await appointment_service.delete_appointment(current_user.id, appointment_id)
