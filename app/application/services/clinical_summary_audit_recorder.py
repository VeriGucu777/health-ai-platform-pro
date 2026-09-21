"""Fail-open clinical summary audit recording helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.application.dtos.audit_log import AuditRecordInput
from app.application.dtos.auth_audit import AuthAuditContext
from app.application.dtos.user import UserDTO
from app.core.logging import get_logger
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType

if TYPE_CHECKING:
    from app.application.services.audit_service import AuditService

logger = get_logger(__name__)


async def record_clinical_summary_audit_event(
    audit_service: AuditService | None,
    *,
    outcome: AuditOutcome,
    http_status: int,
    audit_context: AuthAuditContext | None,
    current_user: UserDTO,
    patient_id: UUID,
    metadata: dict[str, Any] | None = None,
    organization_id: UUID | None = None,
) -> None:
    """Persist a clinical summary view audit event without breaking the HTTP response."""
    if audit_service is None or audit_context is None:
        return

    entry = AuditRecordInput(
        resource_type=AuditResourceType.PATIENT_CLINICAL_SUMMARY,
        action=AuditAction.VIEW,
        outcome=outcome,
        http_status=http_status,
        actor_id=current_user.id,
        actor_role=current_user.role,
        owner_scope_id=current_user.id,
        resource_id=patient_id,
        request_id=audit_context.request_id,
        route_template=audit_context.route_template,
        client_ip_truncated=audit_context.client_ip_truncated,
        organization_id=organization_id,
        metadata=metadata,
    )

    try:
        await audit_service.record(entry)
    except Exception:
        logger.exception(
            "Failed to persist clinical summary audit event",
            extra={
                "audit_action": AuditAction.VIEW.value,
                "audit_outcome": outcome.value,
                "http_status": http_status,
                "request_id": audit_context.request_id,
            },
        )
