"""Port for append-only risk assessment history."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.risk.enums import RiskAssessmentType


class RiskAssessmentHistoryRepository(ABC):
    """Risk assessment history — append for new runs; ops-only update for soft-deactivate."""

    @abstractmethod
    async def append(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        """Persist a new immutable history row."""

    @abstractmethod
    async def get_by_id(
        self,
        row_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> RiskAssessmentHistory | None:
        """Load one history row by primary key."""

    @abstractmethod
    async def update(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        """Ops-only persistence for soft-deactivate (no hard delete)."""

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
        include_inactive: bool = False,
    ) -> list[RiskAssessmentHistory]:
        """List history for a patient, newest first (active rows only by default)."""

    @abstractmethod
    async def count_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
        include_inactive: bool = False,
    ) -> int:
        """Count history rows matching filters (active rows only by default)."""
