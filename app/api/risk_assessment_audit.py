"""Shared risk assessment endpoint audit wrapper."""

from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from fastapi import Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.risk_assessment_audit_recorder import (
    RiskKind,
    record_risk_assessment_audit_event,
)
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome

T = TypeVar("T")


async def run_risk_assessment_with_audit(
    *,
    request: Request,
    current_user: UserDTO,
    patient_id: UUID,
    risk_kind: RiskKind,
    audit_service: AuditService,
    assess: Callable[[], Awaitable[tuple[T, UUID | None]]],
) -> T:
    """Execute a risk assessment and record success/failure audit events (fail-open)."""
    audit_context = build_auth_audit_context(request)
    organization_id: UUID | None = None
    try:
        result, organization_id = await assess()
    except AppException as exc:
        await record_risk_assessment_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            risk_kind=risk_kind,
            organization_id=organization_id,
        )
        raise

    await record_risk_assessment_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        risk_kind=risk_kind,
        organization_id=organization_id,
    )
    return result
