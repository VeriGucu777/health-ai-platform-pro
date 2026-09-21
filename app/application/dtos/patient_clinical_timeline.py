"""Patient clinical timeline application DTOs."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.core.reference_ranges import CLINICAL_TIMELINE_DISCLAIMER


class TimelineSourceDTO(BaseSchema):
    """Reference to the data source behind a timeline event."""

    kind: str
    id: UUID


class TimelineEventDTO(BaseSchema):
    """One timeline event returned to the API layer."""

    occurred_at: datetime
    event_type: str
    headline: str
    detail: str
    source: TimelineSourceDTO
    severity: str | None = None


class PatientClinicalTimelineDTO(BaseSchema):
    """Full clinical timeline payload for one owned patient."""

    patient_id: UUID
    date_from: datetime | None
    date_to: datetime
    generated_at: datetime
    events: list[TimelineEventDTO]
    truncated: bool
    disclaimer: str = CLINICAL_TIMELINE_DISCLAIMER
