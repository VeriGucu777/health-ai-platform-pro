"""Fail-open clinical RBAC denied audit recording."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from app.application.dtos.audit_log import AuditRecordInput
from app.application.dtos.auth_audit import AuthAuditContext
from app.application.dtos.user import UserDTO
from app.core.logging import get_logger
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType

if TYPE_CHECKING:
    from app.application.services.audit_service import AuditService

logger = get_logger(__name__)


async def record_clinical_rbac_denied_audit_event(
    audit_service: AuditService | None,
    *,
    audit_context: AuthAuditContext,
    current_user: UserDTO,
    resource_type: AuditResourceType,
    action: AuditAction,
    resource_id: UUID | None,
) -> None:
    """Persist a denied clinical access audit event without affecting the HTTP response."""
    if audit_service is None:
        return

    entry = AuditRecordInput(
        resource_type=resource_type,
        action=action,
        outcome=AuditOutcome.DENIED,
        http_status=403,
        actor_id=current_user.id,
        actor_role=current_user.role,
        owner_scope_id=current_user.id,
        resource_id=resource_id,
        request_id=audit_context.request_id,
        route_template=audit_context.route_template,
        client_ip_truncated=audit_context.client_ip_truncated,
        metadata=None,
    )

    try:
        await audit_service.record(entry)
    except Exception:
        logger.exception(
            "Failed to persist clinical RBAC denied audit event",
            extra={
                "audit_action": action.value,
                "resource_type": resource_type.value,
                "request_id": audit_context.request_id,
            },
        )
