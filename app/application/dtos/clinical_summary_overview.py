"""Clinical summary overview bullet DTOs."""

from datetime import datetime
from typing import Literal

from app.application.dtos.base import BaseSchema

OverviewSeverity = Literal["normal", "info", "warning", "urgent"]


class ClinicalSummaryOverviewItemDTO(BaseSchema):
    """One deterministic overview bullet for clinician-facing summary cards."""

    key: str
    severity: OverviewSeverity
    label: str
    message: str
    trend_status: str | None = None
    source_count: int = 0
    data_window_start: datetime | None = None
    data_window_end: datetime | None = None
