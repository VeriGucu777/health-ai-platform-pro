"""PHI-safe audit for risk assessment history reads."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.risk_assessment_audit_recorder import record_risk_assessment_audit_event
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditAction, AuditOutcome


async def audit_risk_history_list(
    *,
    request: Request,
    current_user: UserDTO,
    audit_service: AuditService,
    patient_id: UUID,
    organization_id: UUID | None,
    assessment_type: str | None,
    page: int,
    page_size: int,
    load,
):
    audit_context = build_auth_audit_context(request)
    metadata: dict[str, str | int] = {"page": page, "page_size": page_size}
    if assessment_type is not None:
        metadata["assessment_type"] = assessment_type
    try:
        result, resolved_org_id = await load()
    except AppException as exc:
        await record_risk_assessment_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            risk_kind="history",
            organization_id=organization_id,
            action_override=AuditAction.LIST,
            metadata=metadata,
        )
        raise

    await record_risk_assessment_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        risk_kind="history",
        organization_id=resolved_org_id,
        action_override=AuditAction.LIST,
        metadata=metadata,
    )
    return result
