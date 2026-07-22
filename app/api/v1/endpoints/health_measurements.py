"""Health measurement CRUD endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, get_health_measurement_service
from app.api.schemas.health_measurement import (
    HealthMeasurementCreate,
    HealthMeasurementListResponse,
    HealthMeasurementResponse,
    HealthMeasurementSortOrder,
    HealthMeasurementUpdate,
)
from app.application.dtos.health_measurement import HealthMeasurementDTO, HealthMeasurementListDTO
from app.application.services.health_measurement_service import HealthMeasurementService

router = APIRouter()


def _health_measurement_response(measurement: HealthMeasurementDTO) -> HealthMeasurementResponse:
    return HealthMeasurementResponse.model_validate(measurement.model_dump())


def _health_measurement_list_response(data: HealthMeasurementListDTO) -> HealthMeasurementListResponse:
    return HealthMeasurementListResponse(
        items=[_health_measurement_response(item) for item in data.items],
        total=data.total,
        page=data.page,
        page_size=data.page_size,
        pages=data.pages,
    )


@router.post(
    "",
    response_model=HealthMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create health measurement",
)
async def create_health_measurement(
    body: HealthMeasurementCreate,
    current_user: CurrentUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
) -> HealthMeasurementResponse:
    """Create a health measurement for a patient owned by the authenticated user."""
    measurement = await health_measurement_service.create_health_measurement(
        current_user.id,
        patient_id=body.patient_id,
        measured_at=body.measured_at,
        blood_glucose=body.blood_glucose,
        glucose_context=body.glucose_context,
        systolic_pressure=body.systolic_pressure,
        diastolic_pressure=body.diastolic_pressure,
        heart_rate=body.heart_rate,
        weight_kg=body.weight_kg,
        insulin_units=body.insulin_units,
        meal_context=body.meal_context,
        exercise_minutes=body.exercise_minutes,
        notes=body.notes,
    )
    return _health_measurement_response(measurement)


@router.get(
    "",
    response_model=HealthMeasurementListResponse,
    summary="List health measurements",
)
async def list_health_measurements(
    current_user: CurrentUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    glucose_context: str | None = None,
    sort_order: HealthMeasurementSortOrder = "desc",
) -> HealthMeasurementListResponse:
    """List health measurements belonging to the authenticated user."""
    measurements = await health_measurement_service.list_health_measurements(
        current_user.id,
        page=page,
        page_size=page_size,
        patient_id=patient_id,
        date_from=date_from,
        date_to=date_to,
        glucose_context=glucose_context,
        sort_order=sort_order,
    )
    return _health_measurement_list_response(measurements)


@router.get(
    "/{health_measurement_id}",
    response_model=HealthMeasurementResponse,
    summary="Get health measurement",
)
async def get_health_measurement(
    health_measurement_id: UUID,
    current_user: CurrentUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
) -> HealthMeasurementResponse:
    """Retrieve a single health measurement owned by the authenticated user."""
    measurement = await health_measurement_service.get_health_measurement(
        current_user.id,
        health_measurement_id,
    )
    return _health_measurement_response(measurement)


@router.patch(
    "/{health_measurement_id}",
    response_model=HealthMeasurementResponse,
    summary="Update health measurement",
)
async def update_health_measurement(
    health_measurement_id: UUID,
    body: HealthMeasurementUpdate,
    current_user: CurrentUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
) -> HealthMeasurementResponse:
    """Update a health measurement owned by the authenticated user."""
    patch = body.model_dump(exclude_unset=True)
    measurement = await health_measurement_service.update_health_measurement(
        current_user.id,
        health_measurement_id,
        patch,
    )
    return _health_measurement_response(measurement)


@router.delete(
    "/{health_measurement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete health measurement",
)
async def delete_health_measurement(
    health_measurement_id: UUID,
    current_user: CurrentUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
) -> None:
    """Delete a health measurement owned by the authenticated user."""
    await health_measurement_service.delete_health_measurement(
        current_user.id,
        health_measurement_id,
    )
