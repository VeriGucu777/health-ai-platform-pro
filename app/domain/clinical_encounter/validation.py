"""Shared validation helpers for clinical encounter domain."""

from datetime import datetime

from app.domain.clinical_encounter.enums import SUPPORTED_ENCOUNTER_LOCALES
from app.domain.clinical_encounter.exceptions import InvalidEncounterFieldError


def require_timezone_aware(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidEncounterFieldError(f"{field_name} must be timezone-aware")
    return value


def validate_specialty_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise InvalidEncounterFieldError("specialty_key must be non-empty")
    if len(normalized) > 64:
        raise InvalidEncounterFieldError("specialty_key exceeds max length")
    return normalized


def validate_encounter_locale(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_ENCOUNTER_LOCALES:
        raise InvalidEncounterFieldError(f"unsupported encounter locale: {value!r}")
    return normalized


def validate_encounter_version(value: int) -> int:
    if value < 1:
        raise InvalidEncounterFieldError("version must be >= 1")
    return value


def validate_time_range(*, started_at: datetime | None, ended_at: datetime | None) -> None:
    if started_at is None or ended_at is None:
        return
    require_timezone_aware(started_at, field_name="started_at")
    require_timezone_aware(ended_at, field_name="ended_at")
    if ended_at < started_at:
        raise InvalidEncounterFieldError("ended_at must not be before started_at")
