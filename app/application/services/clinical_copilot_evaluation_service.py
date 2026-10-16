"""Clinical Copilot technical evaluation — context assembly + engine (no clinical rules in pilot)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from app.application.analytics.risk_assessment_common import calculate_age_years
from app.application.clinical_copilot.constants import (
    CARDIOLOGY_SPECIALTY_KEY,
    HYPERTENSION_CONTEXT_PROFILE_V1,
)
from app.application.clinical_copilot.exceptions import (
    ClinicalCopilotContextProfileError,
    ClinicalCopilotEvaluationUnavailableError,
)
from app.application.clinical_decision.encounter_context_mapper import (
    EncounterContextAssemblyRequest,
    assemble_encounter_evaluation_context_with_snapshot,
)
from app.application.clinical_decision.evaluation_context_snapshot import (
    EvaluationContextSnapshotMetadata,
)
from app.application.clinical_decision.vocabulary_eligibility import VocabularyEligibilityMode
from app.application.clinical_encounter.audit_events import ClinicalEncounterAuditEvent
from app.application.clinical_encounter.audit_hook import ClinicalEncounterAuditHook
from app.application.clinical_encounter.exceptions import ClinicalEncounterNotFoundError
from app.application.services.clinical_encounter_audit_recorder import ClinicalEncounterAuditRecorder
from app.application.services.clinical_patient_child_service import ClinicalPatientChildService
from app.application.clinical_vocabulary.manifest_hash import vocabulary_manifest_hash
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.audit.taxonomy import AuditOutcome
from app.domain.clinical_decision.interfaces.clinical_decision_engine import ClinicalDecisionEnginePort
from app.domain.clinical_decision.models import (
    ClinicalDecisionEvaluationResult,
    PatientDemographicsInput,
)
from app.domain.clinical_encounter.enums import EncounterStatus
from app.domain.clinical_encounter.interfaces.clinical_encounter_repository import (
    ClinicalEncounterRepository,
)
from app.domain.clinical_vocabulary.interfaces.registry import ClinicalVocabularyRegistry
from app.domain.entities.user import UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from app.domain.interfaces.patient_repository import PatientRepository


@dataclass(frozen=True, slots=True)
class ClinicalCopilotEvaluationResponseData:
    """Application-layer evaluation payload (maps to API schema)."""

    result: ClinicalDecisionEvaluationResult
    snapshot: EvaluationContextSnapshotMetadata
    patient_id: UUID
    context_profile: str
    read_only: bool


class ClinicalCopilotEvaluationService(ClinicalPatientChildService):
    """Assemble encounter evaluation context and run the configured decision engine."""

    _EVALUATION_STATUSES = frozenset({EncounterStatus.ACTIVE, EncounterStatus.FINALIZED})

    def __init__(
        self,
        encounter_repository: ClinicalEncounterRepository,
        patient_repository: PatientRepository,
        *,
        access_policy=None,
        membership_repository: OrganizationMembershipRepository | None = None,
        settings: Settings | None = None,
        consent_repository: PatientConsentRepository | None = None,
        vocabulary_registry: ClinicalVocabularyRegistry | None = None,
        engine: ClinicalDecisionEnginePort | None = None,
        engine_factory: Callable[[str], ClinicalDecisionEnginePort] | None = None,
        audit_hook: ClinicalEncounterAuditHook | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(
            patient_repository,
            access_policy=access_policy,
            membership_repository=membership_repository,
            settings=settings,
            consent_repository=consent_repository,
        )
        self._encounters = encounter_repository
        self._vocabulary = vocabulary_registry
        self._engine = engine
        self._engine_factory = engine_factory
        self._audit = audit_hook
        self._clock = clock or (lambda: datetime.now(UTC))

    async def evaluate_encounter(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        encounter_id: UUID,
        context_profile: str = HYPERTENSION_CONTEXT_PROFILE_V1,
    ) -> ClinicalCopilotEvaluationResponseData:
        self._validate_context_profile(context_profile)

        aggregate = await self._encounters.get_by_id(encounter_id)
        if aggregate is None:
            raise ClinicalEncounterNotFoundError()
        enc = aggregate.encounter
        if enc.patient_id != patient_id:
            raise ClinicalEncounterNotFoundError()
        await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.READ,
        )
        if not self._organization_visible(enc.organization_id, actor_role):
            raise ClinicalEncounterNotFoundError()

        read_only = enc.status == EncounterStatus.FINALIZED
        if enc.status not in self._EVALUATION_STATUSES:
            raise ClinicalCopilotEvaluationUnavailableError()
        if (
            context_profile == HYPERTENSION_CONTEXT_PROFILE_V1
            and enc.specialty_key != CARDIOLOGY_SPECIALTY_KEY
        ):
            raise ClinicalCopilotContextProfileError(
                "Hypertension context profile requires cardiology specialty encounter",
            )

        await self._record_audit(
            operation="copilot_evaluation_requested",
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=enc.organization_id,
            patient_id=patient_id,
            encounter_id=enc.id,
            encounter_version=enc.version,
            encounter_status=enc.status.value,
            specialty_key=enc.specialty_key,
            context_profile=context_profile,
        )

        try:
            patient = await self._patients.get_by_id(patient_id)
            if patient is None:
                raise NotFoundError("Patient not found")

            reference_at = self._clock()
            demographics = self._demographics_from_patient(patient, reference_at)
            vocab_hash = None
            if self._vocabulary is not None:
                vocab_hash = vocabulary_manifest_hash(self._vocabulary.manifest())

            assembly = assemble_encounter_evaluation_context_with_snapshot(
                EncounterContextAssemblyRequest(
                    aggregate=aggregate,
                    patient_demographics=demographics,
                    historical_context=None,
                    health_measurements=(),
                    locale=enc.locale,  # type: ignore[arg-type]
                    reference_at=reference_at,
                    vocabulary_registry=self._vocabulary,
                    vocabulary_manifest_hash=vocab_hash,
                    vocabulary_mode=VocabularyEligibilityMode.DEMO,
                    validate_vocabulary_keys=False,
                ),
            )
            engine = self._resolve_engine(enc.specialty_key)
            result = engine.evaluate(assembly.context)

            await self._record_audit(
                operation="copilot_evaluation_succeeded",
                actor_id=actor_id,
                actor_role=actor_role,
                organization_id=enc.organization_id,
                patient_id=patient_id,
                encounter_id=enc.id,
                encounter_version=enc.version,
                encounter_status=enc.status.value,
                specialty_key=enc.specialty_key,
                context_profile=context_profile,
                input_snapshot_id=assembly.snapshot.input_snapshot_id,
                engine_version=result.engine_version,
                evaluation_id=result.evaluation_id,
            )
            return ClinicalCopilotEvaluationResponseData(
                result=result,
                snapshot=assembly.snapshot,
                patient_id=patient_id,
                context_profile=context_profile,
                read_only=read_only,
            )
        except Exception:
            await self._record_audit(
                operation="copilot_evaluation_failed",
                actor_id=actor_id,
                actor_role=actor_role,
                organization_id=enc.organization_id,
                patient_id=patient_id,
                encounter_id=enc.id,
                encounter_version=enc.version,
                encounter_status=enc.status.value,
                specialty_key=enc.specialty_key,
                context_profile=context_profile,
                outcome=AuditOutcome.FAILURE,
            )
            raise

    def _resolve_engine(self, specialty_key: str) -> ClinicalDecisionEnginePort:
        if self._engine is not None:
            return self._engine
        if self._engine_factory is not None:
            return self._engine_factory(specialty_key)
        msg = "Clinical decision engine is not configured"
        raise ValidationError(msg)

    @staticmethod
    def _validate_context_profile(context_profile: str) -> None:
        normalized = context_profile.strip()
        if normalized != HYPERTENSION_CONTEXT_PROFILE_V1:
            raise ClinicalCopilotContextProfileError(
                f"Unsupported context profile {context_profile!r}",
            )

    @staticmethod
    def _demographics_from_patient(patient, reference_at: datetime) -> PatientDemographicsInput:
        age = calculate_age_years(patient.date_of_birth, as_of=reference_at)
        gender_key = patient.gender.strip().lower() if patient.gender else None
        return PatientDemographicsInput(age_years=age, gender_key=gender_key)

    @staticmethod
    def _organization_visible(organization_id: UUID, actor_role: UserRole) -> bool:
        return organization_id is not None or actor_role == UserRole.DOCTOR

    async def _record_audit(
        self,
        *,
        operation: str,
        actor_id: UUID,
        actor_role: UserRole,
        organization_id: UUID,
        patient_id: UUID,
        encounter_id: UUID,
        encounter_version: int,
        encounter_status: str,
        specialty_key: str,
        context_profile: str,
        input_snapshot_id: str | None = None,
        engine_version: str | None = None,
        evaluation_id: UUID | None = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
    ) -> None:
        if self._audit is None:
            return
        event = ClinicalEncounterAuditEvent(
            operation=operation,
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=organization_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            encounter_version=encounter_version,
            encounter_status=encounter_status,
            specialty_key=specialty_key,
            context_profile=context_profile,
            input_snapshot_id=input_snapshot_id,
            engine_version=engine_version,
            evaluation_id=evaluation_id,
        )
        if isinstance(self._audit, ClinicalEncounterAuditRecorder):
            await self._audit.record(event, outcome=outcome)
        else:
            await self._audit.record_event(event)
