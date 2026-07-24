"""Shared DTOs and mappers for on-demand risk assessments."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.application.dtos.health_measurement_insights import HealthRecommendationDTO


class MissingInputDTO(BaseSchema):
    """One required or optional input that is absent or incomplete."""

    input: str
    reason: str
    impact: str


class ContributingFactorDTO(BaseSchema):
    """One explainable factor derived from supplied inputs."""

    factor: str
    status: str
    severity: str
    weight: float
    message: str
    source: str


def map_recommendations(items: object) -> list[HealthRecommendationDTO]:
    """Map model recommendation items to shared health recommendation DTOs."""
    return [
        HealthRecommendationDTO(
            category=item.category,
            message=item.message,
            related_metrics=list(item.related_metrics),
        )
        for item in items  # type: ignore[attr-defined]
    ]


def map_model_result_fields(model_result: object) -> dict[str, object]:
    """Map a rule-based risk model result to shared assessment DTO fields."""
    return {
        "assessment_status": model_result.assessment_status,  # type: ignore[attr-defined]
        "risk_level": model_result.risk_level,  # type: ignore[attr-defined]
        "score": model_result.score,  # type: ignore[attr-defined]
        "probability": model_result.probability,  # type: ignore[attr-defined]
        "contributing_factors": [
            ContributingFactorDTO(**factor.__dict__)
            for factor in model_result.contributing_factors  # type: ignore[attr-defined]
        ],
        "missing_inputs": [
            MissingInputDTO(**item.__dict__)
            for item in model_result.missing_inputs  # type: ignore[attr-defined]
        ],
        "recommendations": map_recommendations(model_result.recommendations),  # type: ignore[attr-defined]
    }


def build_assessment_dto(
    dto_class: type[BaseSchema],
    *,
    patient_id: UUID,
    date_from: datetime,
    date_to: datetime,
    model_version: str,
    model_result: object,
) -> BaseSchema:
    """Build a disease-specific assessment DTO from a shared model result."""
    return dto_class(
        patient_id=patient_id,
        date_from=date_from,
        date_to=date_to,
        model_version=model_version,
        **map_model_result_fields(model_result),
    )
