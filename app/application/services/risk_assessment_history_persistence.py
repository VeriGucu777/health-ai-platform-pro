"""Append immutable risk assessment history after a successful run."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.dtos.base import BaseSchema
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType


def build_result_snapshot(assessment_dto: BaseSchema) -> dict[str, Any]:
    """PHI-safe snapshot of explainability outputs (no raw clinical inputs)."""
    data = assessment_dto.model_dump(mode="json")
    return {
        "date_from": data.get("date_from"),
        "date_to": data.get("date_to"),
        "contributing_factors": data.get("contributing_factors", []),
        "missing_inputs": data.get("missing_inputs", []),
        "recommendations": data.get("recommendations", []),
    }


async def append_risk_assessment_history(
    repository: RiskAssessmentHistoryRepository,
    *,
    patient_id: UUID,
    organization_id: UUID | None,
    assessment_type: RiskAssessmentType,
    evaluated_by_user_id: UUID,
    assessment_dto: BaseSchema,
) -> RiskAssessmentHistory:
    """Persist one history row for a completed assessment (same request, single append)."""
    evaluated_at = datetime.now(UTC)
    entry = RiskAssessmentHistory(
        patient_id=patient_id,
        organization_id=organization_id,
        assessment_type=assessment_type,
        assessment_status=assessment_dto.assessment_status,  # type: ignore[attr-defined]
        risk_level=getattr(assessment_dto, "risk_level", None),
        score=getattr(assessment_dto, "score", None),
        probability=getattr(assessment_dto, "probability", None),
        model_kind=RULE_BASED_MODEL_KIND,
        model_version=assessment_dto.model_version,  # type: ignore[attr-defined]
        evaluated_by_user_id=evaluated_by_user_id,
        evaluated_at=evaluated_at,
        result_snapshot=build_result_snapshot(assessment_dto),
    )
    return await repository.append(entry)
