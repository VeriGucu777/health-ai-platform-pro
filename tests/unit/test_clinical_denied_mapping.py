"""Unit tests for clinical RBAC denied audit route mapping."""

from starlette.requests import Request

from app.domain.audit.clinical_denied_mapping import resolve_clinical_denied_audit
from app.domain.audit.taxonomy import AuditAction, AuditResourceType


def _request(method: str, path: str, route_path: str) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
        "route": type("Route", (), {"path": route_path})(),
        "path_params": {},
    }
    if "{patient_id}" in route_path:
        scope["path_params"] = {"patient_id": "550e8400-e29b-41d4-a716-446655440000"}
    return Request(scope)


def test_patients_list_mapping() -> None:
    mapping = resolve_clinical_denied_audit(
        _request("GET", "/api/v1/patients", ""),
    )
    assert mapping == (AuditResourceType.PATIENT, AuditAction.LIST)


def test_timeline_view_mapping() -> None:
    mapping = resolve_clinical_denied_audit(
        _request("GET", "/api/v1/patients/x/clinical-timeline", "/{patient_id}/clinical-timeline"),
    )
    assert mapping == (AuditResourceType.PATIENT_CLINICAL_TIMELINE, AuditAction.VIEW)


def test_appointments_out_of_scope() -> None:
    mapping = resolve_clinical_denied_audit(
        _request("GET", "/api/v1/appointments", ""),
    )
    assert mapping is None
