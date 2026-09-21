"""Enumerations for patient consent records."""

from enum import StrEnum


class ConsentType(StrEnum):
    """Supported consent categories."""

    CLINICAL_DATA_PROCESSING = "clinical_data_processing"


class ConsentStatus(StrEnum):
    """Lifecycle status of a consent record."""

    GRANTED = "granted"
    REVOKED = "revoked"


class ConsentSource(StrEnum):
    """How the consent record was captured."""

    MANUAL = "manual"
