"""Map in-scope clinical patient routes to audit taxonomy for RBAC denials."""

from __future__ import annotations

from starlette.requests import Request

from app.domain.audit.taxonomy import AuditAction, AuditResourceType

_PATIENTS_PREFIX = "/api/v1/patients"


def resolve_clinical_denied_audit(
    request: Request,
) -> tuple[AuditResourceType, AuditAction] | None:
    """Return audit resource/action for denied access, or None if out of P0 scope."""
    if not request.url.path.startswith(_PATIENTS_PREFIX):
        return None

    route = request.scope.get("route")
    route_template = getattr(route, "path", "") if route is not None else ""
    method = request.method.upper()

    if route_template in ("", "/"):
        if method == "GET":
            return AuditResourceType.PATIENT, AuditAction.LIST
        if method == "POST":
            return AuditResourceType.PATIENT, AuditAction.CREATE
        return None

    if route_template == "/{patient_id}":
        if method == "GET":
            return AuditResourceType.PATIENT, AuditAction.VIEW
        if method == "PATCH":
            return AuditResourceType.PATIENT, AuditAction.UPDATE
        if method == "DELETE":
            return AuditResourceType.PATIENT, AuditAction.DELETE
        return None

    if route_template == "/{patient_id}/clinical-timeline" and method == "GET":
        return AuditResourceType.PATIENT_CLINICAL_TIMELINE, AuditAction.VIEW

    if route_template == "/{patient_id}/clinical-summary" and method == "GET":
        return AuditResourceType.PATIENT_CLINICAL_SUMMARY, AuditAction.VIEW

    if route_template == "/{patient_id}/clinical-retrieval" and method == "POST":
        return AuditResourceType.CLINICAL_RETRIEVAL, AuditAction.SEARCH

    if route_template == "/{patient_id}/clinical-narrative" and method == "POST":
        return AuditResourceType.CLINICAL_NARRATIVE, AuditAction.GENERATE

    if route_template == "/{patient_id}/risk-assessments/diabetes" and method == "GET":
        return AuditResourceType.RISK_ASSESSMENT, AuditAction.EXECUTE
    if route_template == "/{patient_id}/risk-assessments/heart-disease" and method == "GET":
        return AuditResourceType.RISK_ASSESSMENT, AuditAction.EXECUTE
    if route_template == "/{patient_id}/risk-assessments/stroke" and method == "GET":
        return AuditResourceType.RISK_ASSESSMENT, AuditAction.EXECUTE

    if route_template == "/{patient_id}/reports/health-summary.pdf" and method == "GET":
        return AuditResourceType.HEALTH_REPORT, AuditAction.EXPORT

    return None
