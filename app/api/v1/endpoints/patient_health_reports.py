"""Patient health PDF report endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.responses import Response

from app.api.deps import CurrentUser, get_patient_health_report_service
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
    current_user: CurrentUser,
    report_service: Annotated[
        PatientHealthReportService,
        Depends(get_patient_health_report_service),
    ],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    """Generate a PDF health summary for one owned patient within the requested UTC date range."""
    pdf_bytes, filename = await report_service.generate_pdf(
        current_user.id,
        patient_id=patient_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
