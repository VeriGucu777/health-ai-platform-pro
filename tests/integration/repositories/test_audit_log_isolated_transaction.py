"""PostgreSQL tests: audit commits survive business session rollback."""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.dtos.audit_log import AuditRecordInput
from app.application.services.audit_service import AuditService
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.repositories.audit_log_repository import SQLAlchemyAuditLogRepository
from app.infrastructure.repositories.isolated_audit_log_repository import (
    IsolatedSQLAlchemyAuditLogRepository,
)


def _audit_entry(*, request_id: str, action: AuditAction, outcome: AuditOutcome, http_status: int) -> AuditRecordInput:
    return AuditRecordInput(
        resource_type=AuditResourceType.AUTH,
        action=action,
        outcome=outcome,
        http_status=http_status,
        actor_id=None,
        actor_role=None,
        owner_scope_id=None,
        request_id=request_id,
        route_template="/api/v1/auth/login",
        client_ip_truncated="127.0.0.xxx",
        metadata={"reason_code": "invalid_credentials"},
    )


@pytest.fixture
def integration_session_factory(integration_engine):
    return async_sessionmaker(
        bind=integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def _count_audit_rows(session_factory, request_id: str) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(AuditLogModel)
            .where(AuditLogModel.request_id == request_id),
        )
        return int(result.scalar_one())


async def test_shared_session_audit_lost_when_request_session_rolls_back(
    db_session: AsyncSession,
    integration_session_factory,
) -> None:
    request_id = f"rollback-shared-{uuid.uuid4()}"
    shared_repo = SQLAlchemyAuditLogRepository(db_session)
    record = AuditLog(
        resource_type=AuditResourceType.AUTH,
        action=AuditAction.LOGIN_FAILURE,
        outcome=AuditOutcome.FAILURE,
        http_status=401,
        request_id=request_id,
        route_template="/api/v1/auth/login",
        metadata={"reason_code": "invalid_credentials"},
    )
    await shared_repo.append(record)
    await db_session.rollback()

    assert await _count_audit_rows(integration_session_factory, request_id) == 0


async def test_isolated_audit_survives_business_session_rollback(
    db_session: AsyncSession,
    integration_session_factory,
) -> None:
    request_id = f"rollback-isolated-{uuid.uuid4()}"
    audit_service = AuditService(
        IsolatedSQLAlchemyAuditLogRepository(session_factory=integration_session_factory),
    )
    await audit_service.record(
        _audit_entry(
            request_id=request_id,
            action=AuditAction.LOGIN_FAILURE,
            outcome=AuditOutcome.FAILURE,
            http_status=401,
        ),
    )
    await db_session.rollback()

    assert await _count_audit_rows(integration_session_factory, request_id) == 1


async def test_isolated_failure_and_denied_outcomes_persist(
    db_session: AsyncSession,
    integration_session_factory,
) -> None:
    failure_id = f"failure-{uuid.uuid4()}"
    denied_id = f"denied-{uuid.uuid4()}"
    audit_service = AuditService(
        IsolatedSQLAlchemyAuditLogRepository(session_factory=integration_session_factory),
    )

    await audit_service.record(
        AuditRecordInput(
            resource_type=AuditResourceType.PATIENT,
            action=AuditAction.VIEW,
            outcome=AuditOutcome.FAILURE,
            http_status=404,
            actor_id=uuid.uuid4(),
            actor_role=None,
            owner_scope_id=uuid.uuid4(),
            resource_id=uuid.uuid4(),
            request_id=failure_id,
            route_template="/api/v1/patients/{patient_id}",
            client_ip_truncated="127.0.0.xxx",
            metadata=None,
        ),
    )
    await audit_service.record(
        AuditRecordInput(
            resource_type=AuditResourceType.PATIENT,
            action=AuditAction.LIST,
            outcome=AuditOutcome.DENIED,
            http_status=403,
            actor_id=uuid.uuid4(),
            actor_role=None,
            owner_scope_id=uuid.uuid4(),
            resource_id=None,
            request_id=denied_id,
            route_template="/api/v1/patients",
            client_ip_truncated="127.0.0.xxx",
            metadata=None,
        ),
    )
    await db_session.rollback()

    assert await _count_audit_rows(integration_session_factory, failure_id) == 1
    assert await _count_audit_rows(integration_session_factory, denied_id) == 1
