"""In-memory audit repository tests."""

import inspect

import pytest

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


def test_audit_log_repository_port_is_append_only() -> None:
    assert "append" in AuditLogRepository.__abstractmethods__
    assert "update" not in AuditLogRepository.__abstractmethods__
    assert "delete" not in AuditLogRepository.__abstractmethods__


@pytest.mark.asyncio
async def test_memory_repository_appends_records() -> None:
    repo = InMemoryAuditLogRepository()
    record = AuditLog(
        resource_type=AuditResourceType.PATIENT,
        action=AuditAction.VIEW,
        outcome=AuditOutcome.SUCCESS,
    )
    stored = await repo.append(record)
    assert stored.id == record.id
    assert len(repo.list_all()) == 1


def test_memory_repository_has_no_update_or_delete_methods() -> None:
    repo = InMemoryAuditLogRepository()
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")
    public_methods = {
        name
        for name, value in inspect.getmembers(repo, predicate=callable)
        if not name.startswith("_")
    }
    assert public_methods == {"append", "list_all"}
