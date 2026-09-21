"""Clinical narrative orchestration — auth → RAG → LLM → validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from app.application.clinical_narrative.constants import (
    DEFAULT_MAX_NARRATIVE_EVIDENCE,
    DEFAULT_NARRATIVE_LANGUAGE,
    DEFAULT_OVERVIEW_QUERY,
    MAX_NARRATIVE_EVIDENCE,
    MAX_QUERY_LENGTH,
    PROMPT_VERSION,
)
from app.application.clinical_narrative.evidence_payload import build_evidence_items
from app.application.clinical_narrative.exceptions import (
    ClinicalNarrativeProviderError,
    ClinicalNarrativeValidationError,
)
from app.application.clinical_narrative.response_mapper import (
    evidence_references_from_retrieval,
    map_deterministic_summary_fallback,
    map_structured_to_narrative,
)
from app.application.clinical_narrative.validator import ClinicalNarrativeValidator
from app.application.dtos.clinical_narrative import PatientClinicalNarrativeDTO
from app.application.services.base import BaseService
from app.application.services.clinical_retrieval_service import ClinicalRetrievalService
from app.application.services.patient_clinical_summary_service import PatientClinicalSummaryService
from app.application.services.patient_read_access import resolve_patient_read_access
from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.user import UserRole
from app.domain.interfaces.clinical_narrative_generator import (
    ClinicalNarrativeGenerator,
    ClinicalNarrativeGeneratorInput,
)
from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository

logger = get_logger(__name__)


class ClinicalNarrativeService(BaseService):
    """Authorized RAG-backed LLM narrative with deterministic fallback."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        retrieval_service: ClinicalRetrievalService,
        summary_service: PatientClinicalSummaryService,
        narrative_generator: ClinicalNarrativeGenerator,
        settings: Settings,
        access_policy: PatientAccessPolicy | None = None,
        validator: ClinicalNarrativeValidator | None = None,
    ) -> None:
        self._patients = patient_repository
        self._retrieval = retrieval_service
        self._summary = summary_service
        self._generator = narrative_generator
        self._settings = settings
        self._access_policy = access_policy
        self._validator = validator or ClinicalNarrativeValidator()

    def provider_info(self):
        return self._generator.provider_info()

    async def generate_narrative(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        *,
        patient_id: UUID,
        query: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        source_types: list[ClinicalEvidenceSourceType] | None = None,
        max_evidence: int | None = None,
        language: Literal["tr", "en"] | None = None,
    ) -> tuple[PatientClinicalNarrativeDTO, UUID | None]:
        resolved = await resolve_patient_read_access(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
        )
        resolved_from = _normalize_datetime(date_from) if date_from is not None else None
        resolved_to = _normalize_datetime(date_to) if date_to is not None else None
        self._validate_date_range(resolved_from, resolved_to)

        lang: Literal["tr", "en"] = language or _default_language(self._settings)
        cleaned_query = (query or "").strip()
        if len(cleaned_query) > MAX_QUERY_LENGTH:
            raise ValidationError(f"query must be at most {MAX_QUERY_LENGTH} characters")
        retrieval_query = cleaned_query or DEFAULT_OVERVIEW_QUERY

        capped_evidence = _cap_max_evidence(max_evidence)
        retrieval_dto, _org = await self._retrieval.search(
            actor_id,
            actor_role,
            patient_id=patient_id,
            query=retrieval_query,
            top_k=capped_evidence,
            source_types=source_types,
            date_from=resolved_from,
            date_to=resolved_to,
        )
        evidence_refs = evidence_references_from_retrieval(retrieval_dto.results)
        evidence_items = build_evidence_items(
            retrieval_dto.results,
            max_items=capped_evidence,
        )
        allowed_ids = {item.evidence_id for item in evidence_items}

        generator_input = ClinicalNarrativeGeneratorInput(
            prompt_version=PROMPT_VERSION,
            language=lang,
            user_query_intent=retrieval_query,
            evidence_items=evidence_items,
            max_output_tokens=self._settings.clinical_narrative_max_output_tokens,
        )

        try:
            structured = await self._generator.generate(generator_input)
            self._validator.validate(
                structured,
                allowed_evidence_ids=allowed_ids,
                evidence_items=evidence_items,
            )
            dto = map_structured_to_narrative(
                patient_id=patient_id,
                language=lang,
                structured=structured,
                evidence_refs=evidence_refs,
            )
            logger.info(
                "Clinical narrative generated provider=%s model=%s evidence_count=%s fallback=false",
                self._generator.provider_info().provider_kind,
                self._generator.provider_info().model_identifier,
                len(evidence_items),
            )
            return dto, resolved.organization_id
        except (ClinicalNarrativeProviderError, ClinicalNarrativeValidationError) as exc:
            logger.warning(
                "Clinical narrative generation failed; using deterministic fallback reason=%s",
                exc.message,
            )
            summary, _ = await self._summary.get_clinical_summary(
                actor_id,
                actor_role,
                patient_id=patient_id,
                date_from=resolved_from,
                date_to=resolved_to,
            )
            dto = map_deterministic_summary_fallback(
                patient_id=patient_id,
                language=lang,
                summary=summary,
                evidence_refs=evidence_refs,
                reason=exc.message,
            )
            logger.info(
                "Clinical narrative fallback provider=%s evidence_count=%s fallback=true",
                self._generator.provider_info().provider_kind,
                len(evidence_items),
            )
            return dto, resolved.organization_id

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> None:
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("date_from must be before or equal to date_to")


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _cap_max_evidence(max_evidence: int | None) -> int:
    requested = max_evidence if max_evidence is not None else DEFAULT_MAX_NARRATIVE_EVIDENCE
    return min(max(1, requested), MAX_NARRATIVE_EVIDENCE)


def _default_language(settings: Settings) -> Literal["tr", "en"]:
    raw = (settings.clinical_narrative_default_language or DEFAULT_NARRATIVE_LANGUAGE).strip().lower()
    if raw == "en":
        return "en"
    return "tr"
