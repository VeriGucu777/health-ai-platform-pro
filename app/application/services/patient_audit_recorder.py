"""Fail-open patient audit recording helpers."""

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


async def record_patient_audit_event(
    audit_service: AuditService | None,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    http_status: int,
    audit_context: AuthAuditContext | None,
    current_user: UserDTO,
    resource_id: UUID | None = None,
    organization_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a patient audit event without affecting the patient API on failure."""
    if audit_service is None or audit_context is None:
        return

    entry = AuditRecordInput(
        resource_type=AuditResourceType.PATIENT,
        action=action,
        outcome=outcome,
        http_status=http_status,
        actor_id=current_user.id,
        actor_role=current_user.role,
        owner_scope_id=current_user.id,
        resource_id=resource_id,
        organization_id=organization_id,
        request_id=audit_context.request_id,
        route_template=audit_context.route_template,
        client_ip_truncated=audit_context.client_ip_truncated,
        metadata=metadata,
    )

    try:
        await audit_service.record(entry)
    except Exception:
        logger.exception(
            "Failed to persist patient audit event",
            extra={
                "audit_action": action.value,
                "audit_outcome": outcome.value,
                "http_status": http_status,
                "request_id": audit_context.request_id,
            },
        )
