"""Summary-level clinical period from overview item data windows."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.dtos.clinical_summary_overview import ClinicalSummaryOverviewItemDTO

# Appointments describe follow-up timing, not the measurement/evidence window.
_APPOINTMENT_OVERVIEW_KEYS = frozenset({"upcoming_follow_up", "overdue_follow_up"})


def compute_overview_clinical_period(
    items: list[ClinicalSummaryOverviewItemDTO],
) -> tuple[datetime | None, datetime | None]:
    """Min/max data window across overview bullets, excluding follow-up appointment rows."""
    starts: list[datetime] = []
    ends: list[datetime] = []
    for item in items:
        if item.key in _APPOINTMENT_OVERVIEW_KEYS:
            continue
        if item.data_window_start is not None:
            starts.append(_as_utc(item.data_window_start))
        if item.data_window_end is not None:
            ends.append(_as_utc(item.data_window_end))
    if not starts or not ends:
        return None, None
    return min(starts), max(ends)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
