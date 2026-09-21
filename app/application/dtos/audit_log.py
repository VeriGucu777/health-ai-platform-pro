"""Audit log application DTOs."""

from typing import Any
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user import UserRole


class AuditRecordInput(BaseSchema):
    """Input for recording a single audit event."""

    resource_type: AuditResourceType
    action: AuditAction
    outcome: AuditOutcome
    actor_id: UUID | None = None
    actor_role: UserRole | None = None
    resource_id: UUID | None = None
    http_status: int | None = None
    request_id: str | None = None
    route_template: str | None = None
    client_ip_truncated: str | None = None
    owner_scope_id: UUID | None = None
    organization_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class AuditLogDTO(BaseSchema):
    """Audit record returned after persistence."""

    id: UUID
    occurred_at: str
    actor_id: UUID | None
    actor_role: UserRole | None
    resource_type: AuditResourceType
    resource_id: UUID | None
    action: AuditAction
    outcome: AuditOutcome
    http_status: int | None
    request_id: str | None
    route_template: str | None
    client_ip_truncated: str | None
    owner_scope_id: UUID | None
    organization_id: UUID | None
    metadata: dict[str, Any] | None

    @classmethod
    def from_entity(cls, record: AuditLog) -> "AuditLogDTO":
        return cls(
            id=record.id,
            occurred_at=record.occurred_at.isoformat(),
            actor_id=record.actor_id,
            actor_role=record.actor_role,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            action=record.action,
            outcome=record.outcome,
            http_status=record.http_status,
            request_id=record.request_id,
            route_template=record.route_template,
            client_ip_truncated=record.client_ip_truncated,
            owner_scope_id=record.owner_scope_id,
            organization_id=record.organization_id,
            metadata=record.metadata,
        )
