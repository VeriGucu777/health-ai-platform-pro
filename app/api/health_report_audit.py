"""Shared health report export endpoint audit wrapper."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import Request, status

from app.api.auth_audit_context import build_auth_audit_context
from app.application.dtos.user import UserDTO
from app.application.services.audit_service import AuditService
from app.application.services.health_report_audit_recorder import (
    record_health_report_export_audit_event,
)
from app.core.exceptions import AppException
from app.domain.audit.taxonomy import AuditOutcome


async def run_health_report_export_with_audit(
    *,
    request: Request,
    current_user: UserDTO,
    patient_id: UUID,
    audit_service: AuditService,
    export_pdf: Callable[[], Awaitable[tuple[bytes, str, UUID | None]]],
) -> tuple[bytes, str]:
    """Execute a PDF export and record success/failure audit events (fail-open)."""
    audit_context = build_auth_audit_context(request)
    organization_id: UUID | None = None
    try:
        pdf_bytes, filename, organization_id = await export_pdf()
    except AppException as exc:
        await record_health_report_export_audit_event(
            audit_service,
            outcome=AuditOutcome.FAILURE,
            http_status=exc.status_code,
            audit_context=audit_context,
            current_user=current_user,
            patient_id=patient_id,
            organization_id=organization_id,
        )
        raise

    await record_health_report_export_audit_event(
        audit_service,
        outcome=AuditOutcome.SUCCESS,
        http_status=status.HTTP_200_OK,
        audit_context=audit_context,
        current_user=current_user,
        patient_id=patient_id,
        organization_id=organization_id,
    )
    return pdf_bytes, filename
