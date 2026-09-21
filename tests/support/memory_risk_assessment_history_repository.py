"""In-memory append-only risk assessment history repository."""

from datetime import datetime
from uuid import UUID

from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType


class InMemoryRiskAssessmentHistoryRepository(RiskAssessmentHistoryRepository):
    """Append-only store for tests — no update/delete API."""

    def __init__(self) -> None:
        self._rows: list[RiskAssessmentHistory] = []

    @property
    def rows(self) -> list[RiskAssessmentHistory]:
        return list(self._rows)

    async def append(self, entry: RiskAssessmentHistory) -> RiskAssessmentHistory:
        self._rows.append(entry)
        return entry

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
        filtered = [r for r in self._rows if r.patient_id == patient_id]
        if assessment_type is not None:
            filtered = [r for r in filtered if r.assessment_type == assessment_type]
        if evaluated_at_from is not None:
            filtered = [r for r in filtered if r.evaluated_at >= evaluated_at_from]
        if evaluated_at_to is not None:
            filtered = [r for r in filtered if r.evaluated_at <= evaluated_at_to]
        filtered.sort(key=lambda r: (r.evaluated_at, r.created_at), reverse=True)
        return filtered[offset : offset + limit]

    async def count_by_patient(
        self,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        evaluated_at_from: datetime | None = None,
        evaluated_at_to: datetime | None = None,
    ) -> int:
        items = await self.list_by_patient(
            patient_id,
            assessment_type=assessment_type,
            evaluated_at_from=evaluated_at_from,
            evaluated_at_to=evaluated_at_to,
            offset=0,
            limit=10_000,
        )
        return len(items)
