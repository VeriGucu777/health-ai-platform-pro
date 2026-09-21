"""Health measurement CRUD endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.clinical_child_read_audit import audit_child_list, audit_child_view
from app.api.deps import ClinicalUser, get_audit_service, get_health_measurement_service
from app.api.schemas.health_measurement import (
    HealthMeasurementCreate,
    HealthMeasurementListResponse,
    HealthMeasurementResponse,
    HealthMeasurementSortOrder,
    HealthMeasurementUpdate,
)
from app.application.dtos.health_measurement import HealthMeasurementDTO, HealthMeasurementListDTO
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_child_audit_recorder import record_clinical_child_audit_event
from app.application.services.health_measurement_service import HealthMeasurementService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

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
        child_kind="health_measurement",
        patient_id=patient_id,
        child_id=child_id,
    )


@router.post(
    "",
    response_model=HealthMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create health measurement",
)
async def create_health_measurement(
    body: HealthMeasurementCreate,
    request: Request,
    current_user: ClinicalUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> HealthMeasurementResponse:
    """Create a health measurement for an accessible patient."""
    audit_context = build_auth_audit_context(request)
    try:
        measurement, organization_id = await health_measurement_service.create_health_measurement(
            current_user.id,
            current_user.role,
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
        child_kind="health_measurement",
        patient_id=measurement.patient_id,
        child_id=measurement.id,
        organization_id=organization_id,
    )
    return _health_measurement_response(measurement)


@router.get(
    "",
    response_model=HealthMeasurementListResponse,
    summary="List health measurements",
)
async def list_health_measurements(
    request: Request,
    current_user: ClinicalUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    patient_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    glucose_context: str | None = None,
    sort_order: HealthMeasurementSortOrder = "desc",
) -> HealthMeasurementListResponse:
    """List health measurements for patients the caller may access."""
    measurements = await audit_child_list(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="health_measurement",
        patient_id=patient_id,
        page=page,
        page_size=page_size,
        policy_service=health_measurement_service,
        load=lambda: health_measurement_service.list_health_measurements(
            current_user.id,
            current_user.role,
            page=page,
            page_size=page_size,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
            glucose_context=glucose_context,
            sort_order=sort_order,
        ),
    )
    return _health_measurement_list_response(measurements)


@router.get(
    "/{health_measurement_id}",
    response_model=HealthMeasurementResponse,
    summary="Get health measurement",
)
async def get_health_measurement(
    health_measurement_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> HealthMeasurementResponse:
    """Retrieve a single health measurement when the linked patient is accessible."""

    async def _load() -> tuple[HealthMeasurementDTO, UUID | None, UUID]:
        measurement, organization_id = await health_measurement_service.get_health_measurement(
            current_user.id,
            current_user.role,
            health_measurement_id,
        )
        return measurement, organization_id, measurement.patient_id

    measurement = await audit_child_view(
        request=request,
        current_user=current_user,
        audit_service=audit_service,
        child_kind="health_measurement",
        child_id=health_measurement_id,
        load=_load,
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
    request: Request,
    current_user: ClinicalUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> HealthMeasurementResponse:
    """Update a health measurement when the linked patient is writable."""
    audit_context = build_auth_audit_context(request)
    patch = body.model_dump(exclude_unset=True)
    try:
        measurement, organization_id = await health_measurement_service.update_health_measurement(
            current_user.id,
            current_user.role,
            health_measurement_id,
            patch,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.UPDATE,
            patient_id=None,
            child_id=health_measurement_id,
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
        child_kind="health_measurement",
        patient_id=measurement.patient_id,
        child_id=measurement.id,
        organization_id=organization_id,
    )
    return _health_measurement_response(measurement)


@router.delete(
    "/{health_measurement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete health measurement",
)
async def delete_health_measurement(
    health_measurement_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    health_measurement_service: Annotated[
        HealthMeasurementService,
        Depends(get_health_measurement_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> None:
    """Delete a health measurement when the linked patient is deletable."""
    audit_context = build_auth_audit_context(request)
    patient_id: UUID | None = None
    try:
        organization_id, patient_id = await health_measurement_service.delete_health_measurement(
            current_user.id,
            current_user.role,
            health_measurement_id,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.DELETE,
            patient_id=patient_id,
            child_id=health_measurement_id,
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
        child_kind="health_measurement",
        patient_id=patient_id,
        child_id=health_measurement_id,
        organization_id=organization_id,
    )
