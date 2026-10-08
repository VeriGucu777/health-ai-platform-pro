"""Clinical encounter application service — access control and workflows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from app.application.clinical_decision.time_ports import ClockPort, SystemUtcClock
from app.application.clinical_encounter.aggregate_ops import (
    append_complaint,
    append_finding,
    deactivate_complaint_by_id,
    record_question_response,
)
from app.application.clinical_encounter.audit_hook import (
    ClinicalEncounterAuditHook,
    NoOpClinicalEncounterAuditHook,
)
from app.application.clinical_encounter.exceptions import (
    ActiveClinicalEncounterAlreadyExists,
    ClinicalEncounterAccessDeniedError,
    ClinicalEncounterApplicationConflictError,
    ClinicalEncounterFinalizationError,
    ClinicalEncounterNotFoundError,
    ClinicalEncounterOwnershipError,
    ClinicalEncounterStaleVersionError,
)
from app.application.clinical_encounter.transaction import ApplicationTransaction
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import EncounterStatus, FindingType, QuestionAnswerType
from app.domain.clinical_encounter.interfaces.clinical_encounter_repository import (
    ClinicalEncounterRepository,
)
from app.domain.entities.user import UserRole
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction
from app.infrastructure.clinical_encounter.exceptions import (
    ClinicalEncounterConcurrencyError,
    ClinicalEncounterConflictError,
    ClinicalEncounterFinalSummaryConflictError,
)


class ClinicalEncounterService(ClinicalPatientChildService):
    """
    Orchestrates encounter lifecycle with PatientAccessPolicy and consent gates.

    New encounters start in ACTIVE status (explicit clinical session start).
    """

    _MUTATION_ROLES = frozenset({UserRole.DOCTOR})

    def __init__(
        self,
        encounter_repository: ClinicalEncounterRepository,
        patient_repository,
        *,
        access_policy=None,
        membership_repository=None,
        settings=None,
        consent_repository=None,
        appointment_repository: AppointmentRepository | None = None,
        transaction: ApplicationTransaction | None = None,
        clock: ClockPort | None = None,
        audit_hook: ClinicalEncounterAuditHook | None = None,
    ) -> None:
        super().__init__(
            patient_repository,
            access_policy,
            membership_repository,
            settings=settings,
            consent_repository=consent_repository,
            enforce_clinical_consent=True,
        )
        self._encounters = encounter_repository
        self._appointments = appointment_repository
        self._transaction = transaction
        self._clock = clock or SystemUtcClock()
        self._audit = audit_hook or NoOpClinicalEncounterAuditHook()

    async def create_encounter(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        organization_id: UUID,
        specialty_key: str,
        locale: str = "en",
        appointment_id: UUID | None = None,
    ) -> ClinicalEncounterAggregate:
        self._require_mutation_role(actor_role)
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.WRITE,
        )
        patient = ctx.patient
        if patient.organization_id is None or patient.organization_id != organization_id:
            raise NotFoundError("Patient not found")
        if ctx.organization_id != organization_id:
            raise NotFoundError("Patient not found")

        if await self._encounters.exists_active_for_patient(patient_id, organization_id):
            raise ActiveClinicalEncounterAlreadyExists()

        if appointment_id is not None:
            await self._validate_appointment_link(
                appointment_id=appointment_id,
                patient_id=patient_id,
                actor_id=actor_id,
                exclude_encounter_id=None,
            )

        now = self._clock.now_utc()
        encounter = ClinicalEncounter.create_draft(
            patient_id=patient_id,
            organization_id=organization_id,
            clinician_user_id=actor_id,
            specialty_key=specialty_key,
            locale=locale,
            appointment_id=appointment_id,
        )
        encounter.activate(at=now)
        aggregate = ClinicalEncounterAggregate(encounter=encounter)

        async def _persist() -> ClinicalEncounterAggregate:
            try:
                created = await self._encounters.add(aggregate)
            except ClinicalEncounterConflictError as exc:
                raise self._map_conflict(exc) from exc
            await self._audit.encounter_created(
                encounter_id=created.encounter.id,
                patient_id=patient_id,
                organization_id=organization_id,
                actor_id=actor_id,
            )
            return created

        return await self._run_unit_of_work(_persist)

    async def get_encounter(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._encounters.get_by_id(encounter_id)
        if aggregate is None:
            raise ClinicalEncounterNotFoundError()
        await self._require_patient_access(
            actor_id,
            actor_role,
            aggregate.encounter.patient_id,
            PatientAccessAction.READ,
        )
        if not self._organization_visible(aggregate.encounter.organization_id, actor_role):
            raise ClinicalEncounterNotFoundError()
        await self._audit.encounter_viewed(
            encounter_id=encounter_id,
            patient_id=aggregate.encounter.patient_id,
            organization_id=aggregate.encounter.organization_id,
            actor_id=actor_id,
        )
        return aggregate

    async def list_patient_encounters(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        organization_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ClinicalEncounterAggregate]:
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.READ,
        )
        org_filter = organization_id
        if ctx.organization_id is not None:
            if org_filter is not None and org_filter != ctx.organization_id:
                raise NotFoundError("Patient not found")
            org_filter = ctx.organization_id
        return await self._encounters.list_for_patient(
            patient_id,
            organization_id=org_filter,
            offset=offset,
            limit=limit,
        )

    async def add_complaint(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
        *,
        complaint_key: str | None = None,
        clinician_display_text: str | None = None,
        is_primary: bool = False,
        negated: bool = False,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        now = self._clock.now_utc()

        async def _persist() -> ClinicalEncounterAggregate:
            updated = append_complaint(
                aggregate,
                complaint_key=complaint_key,
                clinician_display_text=clinician_display_text,
                is_primary=is_primary,
                negated=negated,
                recorded_at=now,
                recorded_by=actor_id,
            )
            return await self._save_aggregate(updated)

        return await self._run_unit_of_work(_persist)

    async def add_finding(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
        *,
        finding_type: FindingType,
        finding_key: str,
        value_code: str | None = None,
        value_numeric: Decimal | None = None,
        unit: str | None = None,
        negated: bool = False,
        onset_code: str | None = None,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        now = self._clock.now_utc()
        finding = EncounterFinding(
            encounter_id=aggregate.encounter.id,
            finding_type=finding_type,
            finding_key=finding_key,
            value_code=value_code,
            value_numeric=value_numeric,
            unit=unit,
            negated=negated,
            onset_code=onset_code,
            recorded_at=now,
            recorded_by=actor_id,
        )

        async def _persist() -> ClinicalEncounterAggregate:
            updated = append_finding(aggregate, finding=finding)
            return await self._save_aggregate(updated)

        return await self._run_unit_of_work(_persist)

    async def record_question_response(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
        *,
        question_key: str,
        answer_type: QuestionAnswerType,
        answer_code: str | None = None,
        answer_numeric: Decimal | None = None,
        clinician_note: str | None = None,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        now = self._clock.now_utc()

        async def _persist() -> ClinicalEncounterAggregate:
            updated = record_question_response(
                aggregate,
                question_key=question_key,
                answer_type=answer_type,
                answer_code=answer_code,
                answer_numeric=answer_numeric,
                clinician_note=clinician_note,
                answered_at=now,
                answered_by=actor_id,
            )
            return await self._save_aggregate(updated)

        return await self._run_unit_of_work(_persist)

    async def deactivate_complaint(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
        complaint_id: UUID,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        now = self._clock.now_utc()

        async def _persist() -> ClinicalEncounterAggregate:
            updated = deactivate_complaint_by_id(aggregate, complaint_id, at=now)
            return await self._save_aggregate(updated)

        return await self._run_unit_of_work(_persist)

    async def finalize_encounter(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
        *,
        summary_sections: tuple[EncounterSummarySection, ...],
        clinician_note: str | None = None,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        if aggregate.final_summary is not None:
            raise ClinicalEncounterFinalizationError("final summary already exists")
        if aggregate.encounter.status != EncounterStatus.ACTIVE:
            raise ValidationError("encounter must be active to finalize")

        now = self._clock.now_utc()

        async def _persist() -> ClinicalEncounterAggregate:
            working = deepcopy(aggregate)
            expected_version = working.encounter.version
            working.encounter.finalize(at=now)
            working.encounter.version = expected_version
            summary = EncounterFinalSummary.create(
                encounter_id=working.encounter.id,
                summary_version=1,
                summary_sections=summary_sections,
                clinician_note=clinician_note,
                finalized_by=actor_id,
                finalized_at=now,
            )
            working = replace(working, final_summary=summary)
            try:
                return await self._save_aggregate(working)
            except ClinicalEncounterFinalSummaryConflictError as exc:
                raise ClinicalEncounterFinalizationError(str(exc)) from exc

        return await self._run_unit_of_work(_persist)

    async def cancel_encounter(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._load_owned_for_mutation(actor_id, actor_role, encounter_id)
        now = self._clock.now_utc()

        async def _persist() -> ClinicalEncounterAggregate:
            working = deepcopy(aggregate)
            expected_version = working.encounter.version
            working.encounter.cancel(at=now)
            working.encounter.version = expected_version
            return await self._save_aggregate(working)

        return await self._run_unit_of_work(_persist)

    async def _load_owned_for_mutation(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        encounter_id: UUID,
    ) -> ClinicalEncounterAggregate:
        aggregate = await self._encounters.get_by_id(encounter_id)
        if aggregate is None:
            raise ClinicalEncounterNotFoundError()
        await self._require_patient_access(
            actor_id,
            actor_role,
            aggregate.encounter.patient_id,
            PatientAccessAction.WRITE,
        )
        self._require_mutation_role(actor_role)
        if aggregate.encounter.clinician_user_id != actor_id:
            raise ClinicalEncounterOwnershipError()
        return aggregate

    async def _save_aggregate(
        self,
        aggregate: ClinicalEncounterAggregate,
    ) -> ClinicalEncounterAggregate:
        try:
            return await self._encounters.save(aggregate)
        except ClinicalEncounterConcurrencyError as exc:
            raise ClinicalEncounterStaleVersionError() from exc
        except ClinicalEncounterConflictError as exc:
            raise self._map_conflict(exc) from exc

    async def _validate_appointment_link(
        self,
        *,
        appointment_id: UUID,
        patient_id: UUID,
        actor_id: UUID,
        exclude_encounter_id: UUID | None,
    ) -> None:
        if self._appointments is None:
            raise ValidationError("appointment linking is not configured")
        appointment = await self._appointments.get_by_id(appointment_id)
        if appointment is None or appointment.patient_id != patient_id:
            raise NotFoundError("Appointment not found")
        if appointment.owner_id != actor_id:
            raise NotFoundError("Appointment not found")
        encounters = await self._encounters.list_for_patient(patient_id)
        for item in encounters:
            if item.encounter.appointment_id == appointment_id and (
                exclude_encounter_id is None or item.encounter.id != exclude_encounter_id
            ):
                raise ClinicalEncounterApplicationConflictError(
                    "appointment already linked to an encounter",
                )

    def _require_mutation_role(self, actor_role: UserRole) -> None:
        if actor_role not in self._MUTATION_ROLES:
            raise ClinicalEncounterAccessDeniedError()

    @staticmethod
    def _organization_visible(organization_id: UUID, actor_role: UserRole) -> bool:
        return organization_id is not None or actor_role == UserRole.DOCTOR

    @staticmethod
    def _map_conflict(exc: ClinicalEncounterConflictError) -> Exception:
        message = str(exc).lower()
        if "active encounter" in message:
            return ActiveClinicalEncounterAlreadyExists()
        if "appointment already linked" in message:
            return ClinicalEncounterApplicationConflictError(str(exc))
        return ClinicalEncounterApplicationConflictError(str(exc))

    async def _run_unit_of_work(self, operation):
        if self._transaction is None:
            return await operation()
        try:
            result = await operation()
            await self._transaction.commit()
            return result
        except Exception:
            await self._transaction.rollback()
            raise
