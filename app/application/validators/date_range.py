"""Shared date-range validation for analytics and risk assessments."""

from datetime import datetime

from app.core.exceptions import ValidationError
from app.core.reference_ranges import MAX_ANALYTICS_DATE_RANGE_DAYS


def validate_analytics_date_range(date_from: datetime, date_to: datetime) -> None:
    """Validate an inclusive analytics or assessment date range."""
    if date_from > date_to:
        raise ValidationError("date_from must be before or equal to date_to")

    if (date_to - date_from).days > MAX_ANALYTICS_DATE_RANGE_DAYS:
        raise ValidationError("Date range cannot exceed 366 days")
