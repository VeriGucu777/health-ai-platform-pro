"""Risk assessment domain enumerations."""

from enum import StrEnum


class RiskAssessmentType(StrEnum):
    """Supported on-demand risk assessment kinds."""

    DIABETES = "diabetes"
    HEART_DISEASE = "heart_disease"
    STROKE = "stroke"


RULE_BASED_MODEL_KIND = "rule_based"
