"""Unit tests for isolated audit log repository session lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.infrastructure.repositories.isolated_audit_log_repository import (
    IsolatedSQLAlchemyAuditLogRepository,
)


@pytest.mark.asyncio
async def test_append_opens_session_commits_and_closes() -> None:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=session)
    repo = IsolatedSQLAlchemyAuditLogRepository(session_factory=factory)

    record = AuditLog(
        resource_type=AuditResourceType.AUTH,
        action=AuditAction.LOGIN_FAILURE,
        outcome=AuditOutcome.FAILURE,
        http_status=401,
        request_id="unit-test-req",
    )
    persisted = AuditLog(
        id=record.id,
        resource_type=record.resource_type,
        action=record.action,
        outcome=record.outcome,
        http_status=record.http_status,
        request_id=record.request_id,
    )

    with patch(
        "app.infrastructure.repositories.isolated_audit_log_repository.SQLAlchemyAuditLogRepository",
    ) as repo_cls:
        inner = AsyncMock()
        inner.append = AsyncMock(return_value=persisted)
        repo_cls.return_value = inner

        result = await repo.append(record)

    factory.assert_called_once()
    session.__aenter__.assert_awaited_once()
    session.__aexit__.assert_awaited_once()
    inner.append.assert_awaited_once_with(record)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    assert result is persisted


@pytest.mark.asyncio
async def test_append_rolls_back_isolated_session_on_failure() -> None:
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=session)
    repo = IsolatedSQLAlchemyAuditLogRepository(session_factory=factory)

    record = AuditLog(
        resource_type=AuditResourceType.AUTH,
        action=AuditAction.LOGIN_SUCCESS,
        outcome=AuditOutcome.SUCCESS,
        http_status=200,
        request_id="unit-test-fail",
    )

    with patch(
        "app.infrastructure.repositories.isolated_audit_log_repository.SQLAlchemyAuditLogRepository",
    ) as repo_cls:
        inner = AsyncMock()
        inner.append = AsyncMock(side_effect=RuntimeError("db down"))
        repo_cls.return_value = inner

        with pytest.raises(RuntimeError, match="db down"):
            await repo.append(record)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
