"""SQLAlchemy clinical encounter aggregate repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinical_encounter.entities import ClinicalEncounterAggregate
from app.domain.clinical_encounter.enums import EncounterStatus
from app.domain.clinical_encounter.interfaces.clinical_encounter_repository import (
    ClinicalEncounterRepository as ClinicalEncounterRepositoryPort,
)
from app.infrastructure.clinical_encounter.exceptions import (
    ClinicalEncounterConcurrencyError,
    ClinicalEncounterConflictError,
    ClinicalEncounterFinalSummaryConflictError,
)
from app.infrastructure.clinical_encounter.mappers import (
    build_aggregate,
    complaint_domain_to_model,
    encounter_domain_to_model,
    final_summary_domain_to_model,
    finding_domain_to_model,
    response_domain_to_model,
)
from app.infrastructure.database.models.clinical_encounter import (
    ClinicalEncounterModel,
    EncounterComplaintModel,
    EncounterFinalSummaryModel,
    EncounterFindingModel,
    EncounterQuestionResponseModel,
)

class SQLAlchemyClinicalEncounterRepository(ClinicalEncounterRepositoryPort):
    """PostgreSQL-backed encounter aggregate repository (flush only; no commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: UUID) -> ClinicalEncounterAggregate | None:
        encounter = await self._session.get(ClinicalEncounterModel, entity_id)
        if encounter is None:
            return None
        return await self._load_aggregate(encounter)

    async def create(self, entity: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        return await self.add(entity)

    async def update(self, entity: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        return await self.save(entity)

    async def delete(self, entity_id: UUID) -> bool:
        instance = await self._session.get(ClinicalEncounterModel, entity_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True

    async def add(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        self._session.add(encounter_domain_to_model(aggregate.encounter))
        for complaint in aggregate.complaints:
            self._session.add(complaint_domain_to_model(complaint))
        for finding in aggregate.findings:
            self._session.add(finding_domain_to_model(finding))
        for response in aggregate.question_responses:
            self._session.add(response_domain_to_model(response))
        if aggregate.final_summary is not None:
            self._session.add(final_summary_domain_to_model(aggregate.final_summary))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ClinicalEncounterConflictError("encounter aggregate insert conflict") from exc
        reloaded = await self.get_by_id(aggregate.encounter.id)
        assert reloaded is not None
        return reloaded

    async def save(self, aggregate: ClinicalEncounterAggregate) -> ClinicalEncounterAggregate:
        encounter = aggregate.encounter
        expected_version = encounter.version
        new_version = expected_version + 1
        stmt = (
            update(ClinicalEncounterModel)
            .where(
                ClinicalEncounterModel.id == encounter.id,
                ClinicalEncounterModel.version == expected_version,
            )
            .values(
                patient_id=encounter.patient_id,
                organization_id=encounter.organization_id,
                clinician_user_id=encounter.clinician_user_id,
                specialty_key=encounter.specialty_key,
                status=encounter.status.value,
                locale=encounter.locale,
                started_at=encounter.started_at,
                ended_at=encounter.ended_at,
                appointment_id=encounter.appointment_id,
                engine_version_at_start=encounter.engine_version_at_start,
                policy_profile_id_at_start=encounter.policy_profile_id_at_start,
                policy_profile_version_at_start=encounter.policy_profile_version_at_start,
                version=new_version,
                is_active=encounter.is_active,
                deleted_at=encounter.deleted_at,
                updated_at=encounter.updated_at,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise ClinicalEncounterConcurrencyError(
                f"stale encounter version {expected_version} for id {encounter.id}",
            )

        await self._upsert_children(aggregate)
        await self._persist_final_summary(aggregate)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ClinicalEncounterConflictError("encounter aggregate save conflict") from exc

        reloaded = await self.get_by_id(encounter.id)
        assert reloaded is not None
        return reloaded

    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        organization_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ClinicalEncounterAggregate]:
        stmt = select(ClinicalEncounterModel).where(ClinicalEncounterModel.patient_id == patient_id)
        if organization_id is not None:
            stmt = stmt.where(ClinicalEncounterModel.organization_id == organization_id)
        stmt = (
            stmt.order_by(
                ClinicalEncounterModel.started_at.desc().nullslast(),
                ClinicalEncounterModel.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        encounters = list(result.scalars().all())
        aggregates: list[ClinicalEncounterAggregate] = []
        for row in encounters:
            aggregates.append(await self._load_aggregate(row))
        return aggregates

    async def get_active_for_patient(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> ClinicalEncounterAggregate | None:
        stmt = select(ClinicalEncounterModel).where(
            ClinicalEncounterModel.patient_id == patient_id,
            ClinicalEncounterModel.organization_id == organization_id,
            ClinicalEncounterModel.status == EncounterStatus.ACTIVE.value,
            ClinicalEncounterModel.is_active.is_(True),
            ClinicalEncounterModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        encounter = result.scalar_one_or_none()
        if encounter is None:
            return None
        return await self._load_aggregate(encounter)

    async def exists_active_for_patient(self, patient_id: UUID, organization_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(ClinicalEncounterModel)
            .where(
                ClinicalEncounterModel.patient_id == patient_id,
                ClinicalEncounterModel.organization_id == organization_id,
                ClinicalEncounterModel.status == EncounterStatus.ACTIVE.value,
                ClinicalEncounterModel.is_active.is_(True),
                ClinicalEncounterModel.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one()) > 0

    async def _load_aggregate(self, encounter: ClinicalEncounterModel) -> ClinicalEncounterAggregate:
        eid = encounter.id
        complaints = await self._load_active_children(EncounterComplaintModel, eid, EncounterComplaintModel.sequence_no)
        findings = await self._load_active_children(EncounterFindingModel, eid, EncounterFindingModel.sequence_no)
        responses = await self._load_active_children(
            EncounterQuestionResponseModel,
            eid,
            EncounterQuestionResponseModel.sequence_no,
        )
        summary_stmt = select(EncounterFinalSummaryModel).where(
            EncounterFinalSummaryModel.encounter_id == eid,
        )
        summary_result = await self._session.execute(summary_stmt)
        final_summary = summary_result.scalar_one_or_none()
        return build_aggregate(
            encounter,
            complaints=complaints,
            findings=findings,
            responses=responses,
            final_summary=final_summary,
        )

    async def _load_active_children(self, model_cls, encounter_id: UUID, order_col):
        stmt = (
            select(model_cls)
            .where(
                model_cls.encounter_id == encounter_id,
                model_cls.is_active.is_(True),
                model_cls.deleted_at.is_(None),
            )
            .order_by(order_col.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _upsert_children(self, aggregate: ClinicalEncounterAggregate) -> None:
        for complaint in aggregate.complaints:
            await self._upsert_row(EncounterComplaintModel, complaint.id, complaint_domain_to_model(complaint))
        for finding in aggregate.findings:
            await self._upsert_row(EncounterFindingModel, finding.id, finding_domain_to_model(finding))
        for response in aggregate.question_responses:
            await self._upsert_row(
                EncounterQuestionResponseModel,
                response.id,
                response_domain_to_model(response),
            )

    async def _upsert_row(self, model_cls, entity_id: UUID, mapped) -> None:
        existing = await self._session.get(model_cls, entity_id)
        if existing is None:
            self._session.add(mapped)
            return
        now = datetime.now(UTC)
        for col in model_cls.__table__.columns:
            if col.name in ("id", "created_at"):
                continue
            if col.name == "updated_at":
                setattr(existing, col.name, now)
                continue
            setattr(existing, col.name, getattr(mapped, col.name))

    async def _persist_final_summary(self, aggregate: ClinicalEncounterAggregate) -> None:
        if aggregate.final_summary is None:
            return
        stmt = select(EncounterFinalSummaryModel).where(
            EncounterFinalSummaryModel.encounter_id == aggregate.encounter.id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            self._session.add(final_summary_domain_to_model(aggregate.final_summary))
            return
        if existing.id != aggregate.final_summary.id:
            raise ClinicalEncounterFinalSummaryConflictError(
                "final summary already exists for encounter",
            )
