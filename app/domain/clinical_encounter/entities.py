"""Clinical encounter aggregate and child entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)
from app.domain.clinical_encounter.exceptions import (
    EncounterAlreadyFinalizedError,
    EncounterCancelledError,
    EncounterImmutableError,
    InvalidEncounterComplaintError,
    InvalidEncounterFieldError,
    InvalidEncounterFinalSummaryError,
    InvalidEncounterFindingError,
    InvalidEncounterTransitionError,
    InvalidQuestionResponseError,
)
from app.domain.clinical_encounter.validation import (
    require_timezone_aware,
    validate_encounter_locale,
    validate_encounter_version,
    validate_specialty_key,
    validate_time_range,
)
from app.domain.entities.base import BaseEntity

BOOLEAN_ANSWER_CODES = frozenset({"yes", "no", "unknown"})


@dataclass(kw_only=True)
class ClinicalEncounter(BaseEntity):
    """Aggregate root for an in-clinic patient encounter session."""

    patient_id: UUID
    organization_id: UUID
    clinician_user_id: UUID
    specialty_key: str
    status: EncounterStatus = EncounterStatus.DRAFT
    locale: str = "en"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    appointment_id: UUID | None = None
    engine_version_at_start: str | None = None
    policy_profile_id_at_start: str | None = None
    policy_profile_version_at_start: str | None = None
    version: int = 1
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.specialty_key = validate_specialty_key(self.specialty_key)
        self.locale = validate_encounter_locale(self.locale)
        self.version = validate_encounter_version(self.version)
        if self.started_at is not None:
            require_timezone_aware(self.started_at, field_name="started_at")
        if self.ended_at is not None:
            require_timezone_aware(self.ended_at, field_name="ended_at")
        validate_time_range(started_at=self.started_at, ended_at=self.ended_at)

    @classmethod
    def create_draft(
        cls,
        *,
        patient_id: UUID,
        organization_id: UUID,
        clinician_user_id: UUID,
        specialty_key: str,
        locale: str = "en",
        appointment_id: UUID | None = None,
        engine_version_at_start: str | None = None,
        policy_profile_id_at_start: str | None = None,
        policy_profile_version_at_start: str | None = None,
    ) -> ClinicalEncounter:
        return cls(
            patient_id=patient_id,
            organization_id=organization_id,
            clinician_user_id=clinician_user_id,
            specialty_key=specialty_key,
            locale=locale,
            status=EncounterStatus.DRAFT,
            appointment_id=appointment_id,
            engine_version_at_start=engine_version_at_start,
            policy_profile_id_at_start=policy_profile_id_at_start,
            policy_profile_version_at_start=policy_profile_version_at_start,
        )

    def is_terminal(self) -> bool:
        return self.status in (EncounterStatus.FINALIZED, EncounterStatus.CANCELLED)

    def assert_mutable(self) -> None:
        if self.status == EncounterStatus.FINALIZED:
            raise EncounterAlreadyFinalizedError("encounter is finalized")
        if self.status == EncounterStatus.CANCELLED:
            raise EncounterCancelledError("encounter is cancelled")
        if not self.is_active or self.deleted_at is not None:
            raise EncounterImmutableError("encounter is not active")

    def _bump_version(self) -> None:
        self.version += 1
        self.touch()

    def activate(self, *, at: datetime) -> None:
        require_timezone_aware(at, field_name="at")
        if self.status == EncounterStatus.DRAFT:
            self.status = EncounterStatus.ACTIVE
            self.started_at = at
            self._bump_version()
            return
        if self.status == EncounterStatus.ACTIVE:
            return
        raise InvalidEncounterTransitionError(
            f"cannot activate encounter from status {self.status.value}",
        )

    def finalize(self, *, at: datetime) -> None:
        require_timezone_aware(at, field_name="at")
        if self.status != EncounterStatus.ACTIVE:
            raise InvalidEncounterTransitionError(
                f"cannot finalize encounter from status {self.status.value}",
            )
        if self.started_at is None:
            raise InvalidEncounterFieldError("started_at required before finalize")
        self.status = EncounterStatus.FINALIZED
        self.ended_at = at
        validate_time_range(started_at=self.started_at, ended_at=self.ended_at)
        self._bump_version()

    def cancel(self, *, at: datetime) -> None:
        require_timezone_aware(at, field_name="at")
        if self.status == EncounterStatus.FINALIZED:
            raise EncounterAlreadyFinalizedError("cannot cancel finalized encounter")
        if self.status == EncounterStatus.CANCELLED:
            return
        if self.status not in (EncounterStatus.DRAFT, EncounterStatus.ACTIVE):
            raise InvalidEncounterTransitionError(
                f"cannot cancel encounter from status {self.status.value}",
            )
        if self.started_at is not None:
            self.ended_at = at
            validate_time_range(started_at=self.started_at, ended_at=self.ended_at)
        else:
            self.ended_at = at
        self.status = EncounterStatus.CANCELLED
        self._bump_version()


@dataclass(kw_only=True)
class EncounterComplaint:
    """Structured or display complaint captured during an encounter."""

    id: UUID = field(default_factory=uuid4)
    encounter_id: UUID
    complaint_key: str | None = None
    clinician_display_text: str | None = field(default=None, repr=False)
    is_primary: bool = False
    negated: bool = False
    sequence_no: int = 1
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    recorded_by: UUID | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        require_timezone_aware(self.recorded_at, field_name="recorded_at")
        if self.deleted_at is not None:
            require_timezone_aware(self.deleted_at, field_name="deleted_at")
        self.validate_contract()

    def validate_contract(self) -> None:
        key = (self.complaint_key or "").strip()
        text = (self.clinician_display_text or "").strip()
        if not key and not text:
            raise InvalidEncounterComplaintError(
                "complaint_key or clinician_display_text is required",
            )
        if self.sequence_no <= 0:
            raise InvalidEncounterComplaintError("sequence_no must be > 0")
        if key:
            self.complaint_key = key
        if text:
            self.clinician_display_text = text
        elif self.clinician_display_text is not None and not text:
            self.clinician_display_text = None

    @property
    def is_engine_safe_key(self) -> bool:
        """Machine rule input uses complaint_key only, never display text."""
        return bool(self.complaint_key)


@dataclass(kw_only=True)
class EncounterFinding:
    """Structured clinical finding (machine keys; explicit negation)."""

    id: UUID = field(default_factory=uuid4)
    encounter_id: UUID
    finding_type: FindingType
    finding_key: str
    value_code: str | None = None
    value_numeric: Decimal | None = None
    unit: str | None = None
    negated: bool = False
    onset_code: str | None = None
    source: ClinicalInputSource = ClinicalInputSource.CLINICIAN_OBSERVED
    sequence_no: int = 1
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    recorded_by: UUID | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        require_timezone_aware(self.recorded_at, field_name="recorded_at")
        if self.deleted_at is not None:
            require_timezone_aware(self.deleted_at, field_name="deleted_at")
        self.validate_contract()

    def validate_contract(self) -> None:
        key = self.finding_key.strip()
        if not key:
            raise InvalidEncounterFindingError("finding_key is required")
        self.finding_key = key
        if self.sequence_no <= 0:
            raise InvalidEncounterFindingError("sequence_no must be > 0")
        if self.value_numeric is not None and self.unit is None:
            raise InvalidEncounterFindingError("unit is required when value_numeric is set")
        if self.unit is not None and len(self.unit.strip()) == 0:
            raise InvalidEncounterFindingError("unit must be non-empty when provided")


@dataclass(frozen=True)
class EncounterSummarySection:
    """One section of a clinician-finalized encounter summary."""

    section_key: str
    content_key: str | None = None
    clinician_text: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        key = self.section_key.strip()
        if not key:
            raise InvalidEncounterFinalSummaryError("section_key is required")
        object.__setattr__(self, "section_key", key)
        if self.content_key is not None:
            ck = self.content_key.strip()
            if not ck:
                raise InvalidEncounterFinalSummaryError("content_key must be non-empty when set")
            object.__setattr__(self, "content_key", ck)


@dataclass(frozen=True)
class EncounterFinalSummary:
    """Immutable clinician final summary (distinct from retrospective Clinical Summary)."""

    id: UUID
    encounter_id: UUID
    summary_version: int
    summary_sections: tuple[EncounterSummarySection, ...]
    finalized_by: UUID
    finalized_at: datetime
    created_at: datetime
    clinician_note: str | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        *,
        encounter_id: UUID,
        summary_version: int,
        summary_sections: tuple[EncounterSummarySection, ...],
        clinician_note: str | None,
        finalized_by: UUID,
        finalized_at: datetime,
        created_at: datetime | None = None,
    ) -> EncounterFinalSummary:
        if summary_version < 1:
            raise InvalidEncounterFinalSummaryError("summary_version must be >= 1")
        if not summary_sections:
            raise InvalidEncounterFinalSummaryError("summary_sections must not be empty")
        finalized_at = require_timezone_aware(finalized_at, field_name="finalized_at")
        created = created_at or finalized_at
        require_timezone_aware(created, field_name="created_at")
        return cls(
            id=uuid4(),
            encounter_id=encounter_id,
            summary_version=summary_version,
            summary_sections=summary_sections,
            clinician_note=clinician_note,
            finalized_by=finalized_by,
            finalized_at=finalized_at,
            created_at=created,
        )


@dataclass(kw_only=True)
class EncounterQuestionResponse:
    """Answer to a structured question_key (copilot/NBQ hook)."""

    id: UUID = field(default_factory=uuid4)
    encounter_id: UUID
    question_key: str
    answer_type: QuestionAnswerType
    answer_code: str | None = None
    answer_numeric: Decimal | None = None
    clinician_note: str | None = field(default=None, repr=False)
    sequence_no: int = 1
    answered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    answered_by: UUID | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        require_timezone_aware(self.answered_at, field_name="answered_at")
        if self.deleted_at is not None:
            require_timezone_aware(self.deleted_at, field_name="deleted_at")
        self.validate_contract()

    def validate_contract(self) -> None:
        qk = self.question_key.strip()
        if not qk:
            raise InvalidQuestionResponseError("question_key is required")
        self.question_key = qk
        if self.sequence_no <= 0:
            raise InvalidQuestionResponseError("sequence_no must be > 0")

        if self.answer_type == QuestionAnswerType.BOOLEAN:
            code = (self.answer_code or "").strip().lower()
            if code not in BOOLEAN_ANSWER_CODES:
                raise InvalidQuestionResponseError(
                    "boolean answer requires answer_code yes/no/unknown",
                )
            self.answer_code = code
        elif self.answer_type == QuestionAnswerType.SINGLE_CHOICE:
            code = (self.answer_code or "").strip()
            if not code:
                raise InvalidQuestionResponseError("single_choice requires answer_code")
            self.answer_code = code
        elif self.answer_type == QuestionAnswerType.NUMBER:
            if self.answer_numeric is None:
                raise InvalidQuestionResponseError("number answer requires answer_numeric")

    def is_engine_evaluable(self) -> bool:
        """Raw text answers are persisted but not auto-mapped to engine rules."""
        return self.answer_type != QuestionAnswerType.TEXT


def assert_child_mutable_for_encounter(encounter: ClinicalEncounter) -> None:
    """Guard child mutations against terminal encounter states."""
    encounter.assert_mutable()


@dataclass(frozen=True)
class ClinicalEncounterAggregate:
    """Loaded/persisted encounter root with operational child collections."""

    encounter: ClinicalEncounter
    complaints: tuple[EncounterComplaint, ...] = ()
    findings: tuple[EncounterFinding, ...] = ()
    question_responses: tuple[EncounterQuestionResponse, ...] = ()
    final_summary: EncounterFinalSummary | None = None
