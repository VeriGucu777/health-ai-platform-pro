"""Patient clinical timeline API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.reference_ranges import CLINICAL_TIMELINE_DISCLAIMER


class TimelineSourceResponse(BaseModel):
    """Reference to the data source behind a timeline event."""

    kind: str
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class TimelineEventResponse(BaseModel):
    """One clinical timeline event."""

    occurred_at: datetime
    event_type: str
    headline: str
    detail: str
    source: TimelineSourceResponse
    severity: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PatientClinicalTimelineResponse(BaseModel):
    """Clinical timeline for one owned patient."""

    patient_id: UUID
    date_from: datetime | None
    date_to: datetime
    generated_at: datetime
    events: list[TimelineEventResponse]
    truncated: bool
    disclaimer: str = Field(
        default=CLINICAL_TIMELINE_DISCLAIMER,
        description="Mandatory decision-support disclaimer for the clinical timeline.",
    )

    model_config = ConfigDict(from_attributes=True)
