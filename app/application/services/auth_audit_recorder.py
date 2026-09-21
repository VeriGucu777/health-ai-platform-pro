"""Fail-open auth audit recording helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.application.dtos.audit_log import AuditRecordInput
from app.application.dtos.auth_audit import AuthAuditContext
from app.core.logging import get_logger
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.user import User, UserRole

if TYPE_CHECKING:
    from app.application.services.audit_service import AuditService

logger = get_logger(__name__)


async def record_auth_audit_event(
    audit_service: AuditService | None,
    *,
    action: AuditAction,
    outcome: AuditOutcome,
    http_status: int,
    audit_context: AuthAuditContext | None,
    actor: User | None = None,
    actor_role: UserRole | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist an auth audit event without affecting the auth flow on failure."""
    if audit_service is None or audit_context is None:
        return

    resolved_actor_id: UUID | None = actor.id if actor is not None else None
    resolved_actor_role = actor.role if actor is not None else actor_role

    entry = AuditRecordInput(
        resource_type=AuditResourceType.AUTH,
        action=action,
        outcome=outcome,
        http_status=http_status,
        actor_id=resolved_actor_id,
        actor_role=resolved_actor_role,
        owner_scope_id=resolved_actor_id,
        request_id=audit_context.request_id,
        route_template=audit_context.route_template,
        client_ip_truncated=audit_context.client_ip_truncated,
        metadata=metadata,
    )

    try:
        await audit_service.record(entry)
    except Exception:
        logger.exception(
            "Failed to persist auth audit event",
            extra={
                "audit_action": action.value,
                "audit_outcome": outcome.value,
                "http_status": http_status,
                "request_id": audit_context.request_id,
            },
        )
