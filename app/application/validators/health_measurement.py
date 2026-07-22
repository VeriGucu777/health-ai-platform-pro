"""Shared validation helpers for health measurements."""

from decimal import Decimal


TRACKABLE_FIELDS = (
    "blood_glucose",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "weight_kg",
    "insulin_units",
    "exercise_minutes",
)


def has_trackable_value(
    *,
    blood_glucose: Decimal | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
    weight_kg: Decimal | None = None,
    insulin_units: Decimal | None = None,
    exercise_minutes: int | None = None,
) -> bool:
    """Return True when at least one trackable measurement value is present."""
    return any(
        value is not None
        for value in (
            blood_glucose,
            systolic_pressure,
            diastolic_pressure,
            heart_rate,
            weight_kg,
            insulin_units,
            exercise_minutes,
        )
    )


def validate_blood_pressure_pair(
    systolic_pressure: int | None,
    diastolic_pressure: int | None,
) -> str | None:
    """Return an error message when only one blood pressure value is provided."""
    if (systolic_pressure is None) != (diastolic_pressure is None):
        return "systolic_pressure and diastolic_pressure must be provided together"
    return None
