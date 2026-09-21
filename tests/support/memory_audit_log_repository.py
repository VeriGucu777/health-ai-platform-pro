"""In-memory append-only audit log repository for tests."""

from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository


class InMemoryAuditLogRepository(AuditLogRepository):
    """Thread-unsafe in-memory audit store — one instance per test."""

    def __init__(self) -> None:
        self.records: list[AuditLog] = []

    async def append(self, record: AuditLog) -> AuditLog:
        self.records.append(record)
        return record

    def list_all(self) -> list[AuditLog]:
        """Test helper — not part of the repository port."""
        return list(self.records)
