"""Immutable risk assessment history snapshot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.entities.base import BaseEntity
from app.domain.risk.enums import RiskAssessmentType


@dataclass(kw_only=True)
class RiskAssessmentHistory(BaseEntity):
    """Append-only historical record of a completed risk assessment run."""

    patient_id: UUID
    organization_id: UUID | None = None
    assessment_type: RiskAssessmentType
    assessment_status: str
    risk_level: str | None = None
    score: float | None = None
    probability: float | None = None
    model_kind: str
    model_version: str
    evaluated_by_user_id: UUID
    evaluated_at: datetime
    result_snapshot: dict[str, Any] | None = None
