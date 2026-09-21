"""Audit log repository port — append-only persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.audit_log import AuditLog


class AuditLogRepository(ABC):
    """Contract for append-only audit log storage."""

    @abstractmethod
    async def append(self, record: AuditLog) -> AuditLog:
        """Persist a new audit record. Updates and deletes are not supported."""
