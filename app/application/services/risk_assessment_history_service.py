"""List immutable risk assessment history under patient READ policy."""

from datetime import datetime
from uuid import UUID

from app.application.dtos.risk_assessment_history import (
    RiskAssessmentHistoryDTO,
    RiskAssessmentHistoryListDTO,
)
from app.application.services.base import BaseService
from app.application.services.patient_read_access import resolve_patient_read_access
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.risk.enums import RiskAssessmentType


class RiskAssessmentHistoryService(BaseService):
    """Read-only access to risk assessment history snapshots."""

    def __init__(
        self,
        history_repository: RiskAssessmentHistoryRepository,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
    ) -> None:
        self._history = history_repository
        self._patients = patient_repository
        self._access_policy = access_policy

    async def list_history_for_user(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        *,
        assessment_type: RiskAssessmentType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[RiskAssessmentHistoryListDTO, UUID | None]:
        resolved = await resolve_patient_read_access(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
        )
        page, page_size, offset = self._normalize_pagination(page, page_size)

        rows = await self._history.list_by_patient(
            patient_id,
            assessment_type=assessment_type,
            evaluated_at_from=date_from,
            evaluated_at_to=date_to,
            offset=offset,
            limit=page_size,
        )
        total = await self._history.count_by_patient(
            patient_id,
            assessment_type=assessment_type,
            evaluated_at_from=date_from,
            evaluated_at_to=date_to,
        )
        items = [RiskAssessmentHistoryDTO.from_entity(row) for row in rows]
        return (
            RiskAssessmentHistoryListDTO.build(items, total=total, page=page, page_size=page_size),
            resolved.organization_id,
        )

    @staticmethod
    def _normalize_pagination(page: int, page_size: int) -> tuple[int, int, int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        offset = (page - 1) * page_size
        return page, page_size, offset
