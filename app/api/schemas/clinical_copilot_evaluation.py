"""Clinical Copilot evaluate API schemas (non-clinical pilot channels only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.clinical_copilot.constants import HYPERTENSION_CONTEXT_PROFILE_V1
from app.domain.clinical_decision.enums import EvaluationStatus


class ClinicalCopilotEvaluateRequest(BaseModel):
    """Optional technical routing identity for the hypertension pilot scaffold."""

    context_profile: str = Field(
        default=HYPERTENSION_CONTEXT_PROFILE_V1,
        min_length=1,
        max_length=64,
    )


class MissingInformationItemResponse(BaseModel):
    information_key: str
    display_key: str
    criticality: str
    rationale_key: str


class ClinicalCopilotProvenanceResponse(BaseModel):
    input_snapshot_id: str
    context_schema_version: str
    vocabulary_id: str | None = None
    vocabulary_version: str | None = None
    vocabulary_manifest_hash: str | None = None
    rule_manifest_hash: str
    engine_version: str
    specialty_module_version: str
    policy_profile_id: str
    policy_profile_version: str
    context_profile: str
    specialty_key: str
    evaluated_at: datetime
    rule_provenance: list = Field(default_factory=list)


class ClinicalCopilotEvaluationResponse(BaseModel):
    """Safe pilot response — no diagnosis, staging, or treatment channels."""

    evaluation_id: UUID
    encounter_id: UUID
    patient_id: UUID
    evaluation_status: EvaluationStatus
    read_only: bool
    missing_information: list[MissingInformationItemResponse] = Field(default_factory=list)
    review_domain_status: list = Field(default_factory=list)
    documentation_reminders: list = Field(default_factory=list)
    provenance: ClinicalCopilotProvenanceResponse
