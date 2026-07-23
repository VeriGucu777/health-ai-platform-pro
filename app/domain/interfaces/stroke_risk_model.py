"""Stroke risk model port for versioned scoring implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

AssessmentStatus = Literal["completed", "insufficient_data"]
RiskLevel = Literal["low", "moderate", "elevated"]


@dataclass(frozen=True)
class StrokeRiskFeatureVector:
    """Structured inputs assembled from owned patient data."""

    age_years: int
    gender: str
    measurement_count: int
    average_systolic_pressure: Decimal | None
    average_diastolic_pressure: Decimal | None
    latest_fasting_glucose: Decimal | None
    latest_non_fasting_glucose: Decimal | None
    structured_medical_record_types: tuple[str, ...]
    stroke_history_record_types: tuple[str, ...]


@dataclass(frozen=True)
class MissingInputItem:
    """One required or optional input that is absent or incomplete."""

    input: str
    reason: str
    impact: str


@dataclass(frozen=True)
class ContributingFactorItem:
    """One explainable factor derived from supplied inputs."""

    factor: str
    status: str
    severity: str
    weight: float
    message: str
    source: str


@dataclass(frozen=True)
class StrokeRiskRecommendationItem:
    """Non-prescriptive monitoring or follow-up recommendation."""

    category: str
    message: str
    related_metrics: tuple[str, ...]


@dataclass(frozen=True)
class StrokeRiskModelResult:
    """Versioned model output before API mapping."""

    assessment_status: AssessmentStatus
    risk_level: RiskLevel | None
    score: float | None
    probability: float | None
    contributing_factors: tuple[ContributingFactorItem, ...]
    missing_inputs: tuple[MissingInputItem, ...]
    recommendations: tuple[StrokeRiskRecommendationItem, ...]


class StrokeRiskModelPort(ABC):
    """Contract for stroke risk scoring models (rule-based or future ML)."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the stable model version identifier exposed in API responses."""

    @abstractmethod
    def assess(self, features: StrokeRiskFeatureVector) -> StrokeRiskModelResult:
        """Compute an informational stroke risk assessment from structured features."""
