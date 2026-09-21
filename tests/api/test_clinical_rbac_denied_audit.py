"""Clinical RBAC 403 denied audit integration tests."""

import json
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user import User, UserRole
from tests.api.test_patient_health_reports import REPORT_DATE_RANGE, _create_patient, _register_and_login
from tests.support.memory_audit_log_repository import InMemoryAuditLogRepository
from tests.support.memory_user_repository import InMemoryUserRepository
from tests.support.risk_assessment_test_helpers import ASSESSMENT_DATE_RANGE, create_patient

REGISTER_PATIENT = {
    "email": "rbac-patient-user@example.com",
    "password": "securepass123",
    "first_name": "Pat",
    "last_name": "User",
    "role": "patient",
}


def _denied_events(repo: InMemoryAuditLogRepository) -> list[AuditLog]:
    return [record for record in repo.list_all() if record.outcome == AuditOutcome.DENIED]


async def _patient_login_headers(client: AsyncClient, *, email: str) -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={**REGISTER_PATIENT, "email": email})
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": REGISTER_PATIENT["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_patient_role_patients_list_writes_denied_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _patient_login_headers(client, email="rbac-deny-list@example.com")
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403

    events = _denied_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].resource_type == AuditResourceType.PATIENT
    assert events[0].action == AuditAction.LIST
    assert events[0].resource_id is None
    assert events[0].http_status == 403
    assert events[0].metadata is None


@pytest.mark.asyncio
async def test_patient_role_timeline_denied_audit_mapping(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    doctor_headers = await _register_and_login(client, email="rbac-doc-timeline@example.com")
    patient_id = await _create_patient(client, doctor_headers)
    patient_headers = await _patient_login_headers(client, email="rbac-pat-timeline@example.com")
    audit_log_repository.records.clear()

    response = await client.get(
        f"/api/v1/patients/{patient_id}/clinical-timeline",
        headers=patient_headers,
    )
    assert response.status_code == 403

    event = _denied_events(audit_log_repository)[0]
    assert event.resource_type == AuditResourceType.PATIENT_CLINICAL_TIMELINE
    assert event.action == AuditAction.VIEW
    assert event.resource_id == UUID(patient_id)


@pytest.mark.asyncio
async def test_patient_role_risk_denied_audit_execute(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    doctor_headers = await _register_and_login(client, email="rbac-doc-risk@example.com")
    patient_id = await create_patient(client, doctor_headers)
    patient_headers = await _patient_login_headers(client, email="rbac-pat-risk@example.com")
    audit_log_repository.records.clear()

    url = f"/api/v1/patients/{patient_id}/risk-assessments/diabetes?{ASSESSMENT_DATE_RANGE}"
    response = await client.get(url, headers=patient_headers)
    assert response.status_code == 403

    event = _denied_events(audit_log_repository)[0]
    assert event.resource_type == AuditResourceType.RISK_ASSESSMENT
    assert event.action == AuditAction.EXECUTE


@pytest.mark.asyncio
async def test_patient_role_pdf_denied_audit_export(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    doctor_headers = await _register_and_login(client, email="rbac-doc-pdf@example.com")
    patient_id = await _create_patient(client, doctor_headers)
    patient_headers = await _patient_login_headers(client, email="rbac-pat-pdf@example.com")
    audit_log_repository.records.clear()

    url = f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?{REPORT_DATE_RANGE}"
    response = await client.get(url, headers=patient_headers)
    assert response.status_code == 403

    event = _denied_events(audit_log_repository)[0]
    assert event.resource_type == AuditResourceType.HEALTH_REPORT
    assert event.action == AuditAction.EXPORT


@pytest.mark.asyncio
async def test_system_admin_clinical_route_writes_denied_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.create(
        User(
            email="rbac-sysadmin@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Sys",
            last_name="Admin",
            role=UserRole.SYSTEM_ADMIN,
        )
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rbac-sysadmin@example.com", "password": "securepass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403

    events = _denied_events(audit_log_repository)
    assert len(events) == 1
    assert events[0].actor_role == UserRole.SYSTEM_ADMIN
    assert events[0].outcome == AuditOutcome.DENIED


@pytest.mark.asyncio
async def test_doctor_success_does_not_write_denied_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _register_and_login(client, email="rbac-doc-ok@example.com")
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    assert len(_denied_events(audit_log_repository)) == 0


@pytest.mark.asyncio
async def test_denied_audit_metadata_contains_no_phi(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _patient_login_headers(
        client,
        email="rbac-phi-deny@example.com",
    )
    audit_log_repository.records.clear()

    await client.get("/api/v1/patients", headers=headers)
    serialized = json.dumps(
        [record.metadata for record in _denied_events(audit_log_repository)],
        default=str,
    )
    assert serialized == "[null]"
    assert "securepass123" not in serialized
    assert "rbac-phi-deny@example.com" not in serialized


@pytest.mark.asyncio
async def test_patient_denied_does_not_create_duplicate_audit_rows(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    headers = await _patient_login_headers(client, email="rbac-dup-deny@example.com")
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403
    assert len(_denied_events(audit_log_repository)) == 1


@pytest.mark.asyncio
async def test_audit_append_failure_does_not_break_403_response(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_append(record: AuditLog) -> AuditLog:
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(audit_log_repository, "append", failing_append)
    headers = await _patient_login_headers(
        client,
        email=f"rbac-fail-open-{uuid4().hex[:8]}@example.com",
    )

    response = await client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_patient_role_appointments_403_without_denied_audit(
    client: AsyncClient,
    audit_log_repository: InMemoryAuditLogRepository,
) -> None:
    """Out-of-scope clinical routers still 403 but do not write P0 denied audit."""
    headers = await _patient_login_headers(client, email="rbac-appt@example.com")
    audit_log_repository.records.clear()

    response = await client.get("/api/v1/appointments", headers=headers)
    assert response.status_code == 403
    assert len(_denied_events(audit_log_repository)) == 0
