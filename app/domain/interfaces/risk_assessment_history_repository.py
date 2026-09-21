"""Port for append-only risk assessment history."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RiskAssessmentType


class RiskAssessmentHistoryRepository(ABC):
    """Append-only persistence for risk assessment history — no update/delete."""

    @abstractmethod
    async def append(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        """Persist a new immutable history row."""

    @abstractmethod
    async def list_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[RiskAssessmentHistory]:
        """List history for a patient, newest first."""

    @abstractmethod
    async def count_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
    ) -> int:
        """Count history rows matching filters."""
