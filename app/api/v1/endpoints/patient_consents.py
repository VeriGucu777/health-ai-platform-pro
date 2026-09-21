"""Clinic admin patient consent management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.api.deps import ClinicAdminUser, get_audit_service, get_patient_consent_service
from app.api.schemas.patient_consent import (
    PatientConsentGrant,
    PatientConsentListResponse,
    PatientConsentResponse,
)
from app.application.dtos.patient_consent import PatientConsentDTO, PatientConsentListDTO
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.patient_consent_audit_recorder import record_patient_consent_audit_event
from app.application.services.patient_consent_service import PatientConsentService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

router = APIRouter()


def _consent_response(data: PatientConsentDTO) -> PatientConsentResponse:
    return PatientConsentResponse.model_validate(data.model_dump())


def _consent_list_response(data: PatientConsentListDTO) -> PatientConsentListResponse:
    return PatientConsentListResponse(items=[_consent_response(item) for item in data.items])


def _consent_metadata(consent: PatientConsentDTO) -> dict[str, str | int]:
    return {
        "consent_type": consent.consent_type.value,
        "status": consent.status.value,
        "version": consent.version,
    }


async def _audit_failure(
    *,
    audit_service: AuditService,
    audit_context,
    current_user: UserDTO,
    action: AuditAction,
    patient_id: UUID,
    service: PatientConsentService,
    metadata: dict | None = None,
    exc: AppException,
) -> None:
    organization_id = await service.resolve_audit_organization_id(current_user.id, patient_id)
    await record_patient_consent_audit_event(
        audit_service,
        action=action,
        outcome=AuditOutcome.FAILURE,
        http_status=exc.status_code,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        organization_id=organization_id,
        metadata=metadata,
    )


@router.get(
    "/{patient_id}/consents",
    response_model=PatientConsentListResponse,
    summary="List patient consent history in the clinic admin organization",
)
async def list_patient_consents(
    patient_id: UUID,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[PatientConsentService, Depends(get_patient_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientConsentListResponse:
    audit_context = build_auth_audit_context(request)
    try:
        consents = await service.list_patient_consents(current_user.id, patient_id)
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.VIEW,
            patient_id=patient_id,
            service=service,
            exc=exc,
        )
        raise

    await record_patient_consent_audit_event(
        audit_service,
        action=AuditAction.VIEW,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        organization_id=consents.organization_id,
    )
    return _consent_list_response(consents)


@router.post(
    "/{patient_id}/consents",
    response_model=PatientConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant a patient consent record",
)
async def grant_patient_consent(
    patient_id: UUID,
    body: PatientConsentGrant,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[PatientConsentService, Depends(get_patient_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientConsentResponse:
    audit_context = build_auth_audit_context(request)
    metadata = {"consent_type": body.consent_type.value}
    try:
        consent = await service.grant_patient_consent(
            current_user.id,
            patient_id,
            consent_type=body.consent_type,
        )
    except AppException as exc:
        await _audit_failure(
            audit_service=audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.GRANT,
            patient_id=patient_id,
            service=service,
            metadata=metadata,
            exc=exc,
        )
        raise

    await record_patient_consent_audit_event(
        audit_service,
        action=AuditAction.GRANT,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_201_CREATED,
        audit_context=audit_context,
        current_user=current_user,
        consent_id=consent.id,
        patient_id=patient_id,
        organization_id=consent.organization_id,
        metadata=_consent_metadata(consent),
    )
    return _consent_response(consent)


@router.patch(
    "/{patient_id}/consents/{consent_id}",
    response_model=PatientConsentResponse,
    summary="Revoke an active patient consent record",
)
async def revoke_patient_consent(
    patient_id: UUID,
    consent_id: UUID,
    request: Request,
    current_user: ClinicAdminUser,
    service: Annotated[PatientConsentService, Depends(get_patient_consent_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> PatientConsentResponse:
    audit_context = build_auth_audit_context(request)
    try:
        consent = await service.revoke_patient_consent(
            current_user.id,
            patient_id,
            consent_id,
        )
    except AppException as exc:
        organization_id = await service.resolve_audit_organization_id(current_user.id, patient_id)
        await record_patient_consent_audit_event(
            audit_service,
            action=AuditAction.REVOKE,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            consent_id=consent_id,
            patient_id=patient_id,
            organization_id=organization_id,
        )
        raise

    await record_patient_consent_audit_event(
        audit_service,
        action=AuditAction.REVOKE,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        consent_id=consent.id,
        patient_id=patient_id,
        organization_id=consent.organization_id,
        metadata=_consent_metadata(consent),
    )
    return _consent_response(consent)
