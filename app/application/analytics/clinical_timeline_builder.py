"""Assemble and sort clinical timeline events."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities.clinical_timeline import ClinicalTimelineEvent


def merge_and_sort_timeline_events(
    event_groups: list[list[ClinicalTimelineEvent]],
) -> list[ClinicalTimelineEvent]:
    """Flatten event groups and sort newest first by occurred_at."""
    merged: list[ClinicalTimelineEvent] = [
        event for group in event_groups for event in group
    ]
    merged.sort(key=lambda event: event.occurred_at, reverse=True)
    return merged


def apply_event_limit(
    events: list[ClinicalTimelineEvent],
    max_events: int,
) -> tuple[list[ClinicalTimelineEvent], bool]:
    """Return capped events and whether truncation occurred."""
    if len(events) <= max_events:
        return events, False
    return events[:max_events], True


def filter_events_by_window(
    events: list[ClinicalTimelineEvent],
    *,
    date_from: datetime | None,
    date_to: datetime,
) -> list[ClinicalTimelineEvent]:
    """Keep events whose occurred_at falls within the inclusive UTC window."""
    filtered: list[ClinicalTimelineEvent] = []
    for event in events:
        occurred = event.occurred_at
        if date_from is not None and occurred < date_from:
            continue
        if occurred > date_to:
            continue
        filtered.append(event)
    return filtered
