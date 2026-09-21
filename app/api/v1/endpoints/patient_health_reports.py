"""Patient health PDF report endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from app.api.deps import ClinicalUser, get_audit_service, get_patient_health_report_service
from app.api.health_report_audit import run_health_report_export_with_audit
from app.application.services.audit_service import AuditService
from app.application.services.patient_health_report_service import PatientHealthReportService

router = APIRouter()


@router.get(
    "/{patient_id}/reports/health-summary.pdf",
    summary="Generate patient health summary PDF report",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Patient health summary PDF report",
        }
    },
)
async def generate_patient_health_summary_pdf(
    patient_id: UUID,
    request: Request,
    current_user: ClinicalUser,
    report_service: Annotated[
        PatientHealthReportService,
        Depends(get_patient_health_report_service),
    ],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    """Generate a PDF health summary for one owned patient within the requested UTC date range."""
    pdf_bytes, filename = await run_health_report_export_with_audit(
        request=request,
        current_user=current_user,
        patient_id=patient_id,
        audit_service=audit_service,
        export_pdf=lambda: report_service.generate_pdf(
            current_user.id,
            current_user.role,
            patient_id=patient_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
