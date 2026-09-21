"""Append-only PHI and security audit logging service."""

from app.application.dtos.audit_log import AuditLogDTO, AuditRecordInput
from app.application.services.base import BaseService
from app.domain.audit.metadata import sanitize_audit_metadata
from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository


class AuditService(BaseService):
    """Sanitizes metadata and appends audit records."""

    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_logs = audit_log_repository

    async def record(self, entry: AuditRecordInput) -> AuditLogDTO:
        """Persist one audit event after metadata sanitization."""
        metadata = sanitize_audit_metadata(entry.metadata)
        record = AuditLog(
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            action=entry.action,
            outcome=entry.outcome,
            http_status=entry.http_status,
            request_id=entry.request_id,
            route_template=entry.route_template,
            client_ip_truncated=entry.client_ip_truncated,
            owner_scope_id=entry.owner_scope_id,
            organization_id=entry.organization_id,
            metadata=metadata,
        )
        created = await self._audit_logs.append(record)
        return AuditLogDTO.from_entity(created)
