"""Clinical timeline domain types."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ClinicalTimelineSource:
    """Pointer to the originating record for a timeline event."""

    kind: str
    id: UUID


@dataclass(frozen=True)
class ClinicalTimelineEvent:
    """One chronological item on a patient clinical timeline."""

    occurred_at: datetime
    event_type: str
    headline: str
    detail: str
    source: ClinicalTimelineSource
    severity: str | None = None
