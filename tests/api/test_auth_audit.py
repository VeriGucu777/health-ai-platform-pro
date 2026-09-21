"""Authentication audit event integration tests."""

import json

import pytest
from httpx import AsyncClient

from app.application.services.audit_service import AuditService
from app.application.services.auth_service import AuthService
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.audit_log_repository import AuditLogRepository
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository

REGISTER_PAYLOAD = {
    "email": "audit-user@example.com",
    "password": "securepass123",
    "first_name": "Audit",
    "last_name": "User",
    "role": "patient",
}


def _auth_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [record for record in repo.list_all() if record.resource_type == AuditResourceType.AUTH]


@pytest.mark.asyncio
async def test_login_success_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200

    events = _auth_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.LOGIN_SUCCESS
    assert event.outcome == AuditOutcome.SUCCESS
    assert event.actor_id is not None
    assert event.http_status == 200


@pytest.mark.asyncio
async def test_login_failure_writes_audit_with_null_actor(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401

    events = _auth_events(audit_log_repository)
    assert len(events) == 1
    event = events[0]
    assert event.action == AuditAction.LOGIN_FAILURE
    assert event.outcome == AuditOutcome.FAILURE
    assert event.actor_id is None
    assert event.metadata == {"reason_code": "invalid_credentials"}


@pytest.mark.asyncio
async def test_login_failure_metadata_contains_no_email_or_password(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    email = "leak-check@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": email},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "not-the-real-password"},
    )

    serialized = json.dumps(
        [record.metadata for record in _auth_events(audit_log_repository)],
        default=str,
    )
    assert email not in serialized
    assert "not-the-real-password" not in serialized
    assert "password" not in serialized.lower()


@pytest.mark.asyncio
async def test_logout_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    audit_log_repository.records.clear()

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert response.status_code == 200

    events = _auth_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.LOGOUT
    assert events[0].outcome == AuditOutcome.SUCCESS


@pytest.mark.asyncio
async def test_change_password_writes_one_audit_row(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    audit_log_repository.records.clear()

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newsecurepass456"},
        headers=headers,
    )
    assert response.status_code == 200

    events = _auth_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].action == AuditAction.PASSWORD_CHANGE
    assert events[0].outcome == AuditOutcome.SUCCESS


@pytest.mark.asyncio
async def test_login_success_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    audit_log_repository.records.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    assert len(_auth_events(audit_log_repository)) == 1


class _FailingAuditLogRepository(AuditLogRepository):
    async def append(self, record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_login(
    user_repository,
    test_settings,
) -> None:
    from app.application.dtos.auth_audit import AuthAuditContext

    auth_service = AuthService(
        user_repository,
        test_settings,
        AuditService(_FailingAuditLogRepository()),
    )
    await auth_service.register(
        email=REGISTER_PAYLOAD["email"],
        password=REGISTER_PAYLOAD["password"],
        first_name=REGISTER_PAYLOAD["first_name"],
        last_name=REGISTER_PAYLOAD["last_name"],
    )

    tokens = await auth_service.login(
        email=REGISTER_PAYLOAD["email"],
        password=REGISTER_PAYLOAD["password"],
        audit_context=AuthAuditContext(
            request_id="req-fail-open",
            route_template="/api/v1/auth/login",
            client_ip_truncated="127.0.0.xxx",
        ),
    )

    assert tokens.access_token
    assert tokens.refresh_token
