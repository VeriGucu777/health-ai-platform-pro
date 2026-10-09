"""Audit repository that always fails append (integration rollback tests)."""

from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository


class FailingAuditLogRepository(AuditLogRepository):
    async def append(self, record: AuditLog) -> AuditLog:
        raise RuntimeError("audit append failed")
