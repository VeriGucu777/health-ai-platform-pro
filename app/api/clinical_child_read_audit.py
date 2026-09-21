"""Shared READ audit wrappers for clinical child HTTP endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from fastapi import Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.clinical_child_audit_recorder import (
    AnalyticsEndpoint,
    ClinicalChildKind,
    build_analytics_read_metadata,
    build_list_read_metadata,
    record_clinical_child_audit_event,
    record_clinical_child_read_failure,
)
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome

T = TypeVar("T")


async def audit_child_list(
    *,
    request: Request,
    current_user: UserDTO,
    audit_service: AuditService,
    child_kind: ClinicalChildKind,
    patient_id: UUID | None,
    page: int,
    page_size: int,
    policy_service: ClinicalPatientChildService,
    load: Callable[[], Awaitable[T]],
) -> T:
    audit_context = build_auth_audit_context(request)
    list_meta = build_list_read_metadata(
        child_kind=child_kind,
        page=page,
        page_size=page_size,
    )
    try:
        result = await load()
    except AppException as exc:
        await record_clinical_child_read_failure(
            audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.LIST,
            http_status=exc.status_code,
            child_kind=child_kind,
            metadata=list_meta,
        )
        raise

    organization_id: UUID | None = None
    audit_patient_id: UUID | None = None
    if patient_id is not None:
        audit_patient_id = patient_id
        organization_id = await policy_service.read_organization_id_for_patient(
            current_user.id,
            current_user.role,
            patient_id,
        )

    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.LIST,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        child_kind=child_kind,
        patient_id=audit_patient_id,
        organization_id=organization_id,
        metadata=list_meta,
    )
    return result


async def audit_child_view(
    *,
    request: Request,
    current_user: UserDTO,
    audit_service: AuditService,
    child_kind: ClinicalChildKind,
    child_id: UUID,
    load: Callable[[], Awaitable[tuple[T, UUID | None, UUID]]],
) -> T:
    """Load returns (dto, organization_id, patient_id)."""
    audit_context = build_auth_audit_context(request)
    try:
        dto, organization_id, patient_id = await load()
    except AppException as exc:
        await record_clinical_child_read_failure(
            audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.VIEW,
            http_status=exc.status_code,
            child_kind=child_kind,
            child_id=child_id,
            metadata={"child_kind": child_kind},
        )
        raise

    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.VIEW,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        child_kind=child_kind,
        patient_id=patient_id,
        child_id=child_id,
        organization_id=organization_id,
        metadata={"child_kind": child_kind},
    )
    return dto


async def audit_analytics_view(
    *,
    request: Request,
    current_user: UserDTO,
    audit_service: AuditService,
    analytics_endpoint: AnalyticsEndpoint,
    patient_id: UUID,
    policy_service: ClinicalPatientChildService,
    date_from: datetime | None,
    date_to: datetime | None,
    period: str | None,
    load: Callable[[], Awaitable[T]],
) -> T:
    audit_context = build_auth_audit_context(request)
    meta = build_analytics_read_metadata(
        analytics_endpoint=analytics_endpoint,
        date_from=date_from,
        date_to=date_to,
        period=period,
    )
    try:
        result = await load()
    except AppException as exc:
        await record_clinical_child_read_failure(
            audit_service,
            audit_context=audit_context,
            current_user=current_user,
            action=AuditAction.VIEW,
            http_status=exc.status_code,
            child_kind="health_measurement",
            metadata=meta,
        )
        raise

    organization_id = await policy_service.read_organization_id_for_patient(
        current_user.id,
        current_user.role,
        patient_id,
    )
    await record_clinical_child_audit_event(
        audit_service,
        action=AuditAction.VIEW,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        child_kind="health_measurement",
        patient_id=patient_id,
        organization_id=organization_id,
        metadata=meta,
    )
    return result
