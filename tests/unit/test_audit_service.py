"""AuditService unit tests."""

from uuid import uuid4

import pytest

from app.application.dtos.audit_log import AuditRecordInput
from app.application.services.audit_service import AuditService
from app.core.exceptions import ValidationError
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.user import UserRole
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository


@pytest.mark.asyncio
async def test_audit_service_record_success() -> None:
    repo = InMemoryAuditLogRepository()
    service = AuditService(repo)
    actor_id = uuid4()
    patient_id = uuid4()

    result = await service.record(
        AuditRecordInput(
            actor_id=actor_id,
            actor_role=UserRole.DOCTOR,
            owner_scope_id=actor_id,
            resource_type=AuditResourceType.PATIENT,
            resource_id=patient_id,
            action=AuditAction.VIEW,
            outcome=AuditOutcome.SUCCESS,
            http_status=200,
            request_id="req-test-1",
            route_template="/api/v1/patients/{patient_id}",
            client_ip_truncated="192.168.1.xxx",
            metadata={"page_size": 20},
        )
    )

    assert result.actor_id == actor_id
    assert result.resource_id == patient_id
    assert result.outcome == AuditOutcome.SUCCESS
    assert len(repo.list_all()) == 1


@pytest.mark.asyncio
async def test_audit_service_rejects_forbidden_metadata() -> None:
    repo = InMemoryAuditLogRepository()
    service = AuditService(repo)

    with pytest.raises(ValidationError):
        await service.record(
            AuditRecordInput(
                resource_type=AuditResourceType.AUTH,
                action=AuditAction.LOGIN_FAILURE,
                outcome=AuditOutcome.FAILURE,
                metadata={"email": "user@example.com"},
            )
        )

    assert len(repo.list_all()) == 0
