"""Immutable clinical knowledge metadata models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.clinical_knowledge.enums import (
    AiUsageStatus,
    ClinicalKnowledgeReviewStatus,
    ClinicalRuleSeverity,
    ClinicalRuleStatus,
    ClinicalRuleType,
    ClinicalSourceType,
    CommercialUsageStatus,
    ConflictStrategy,
    LicenseStatus,
    PolicyProfileStatus,
)


class GuidelineRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    section_ref: str
    recommendation_id: str | None = None


class ClinicalKnowledgeSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    source_type: ClinicalSourceType
    title: str
    publisher_or_organization: str
    edition_or_version: str
    publication_year: int
    official_url: str
    jurisdiction: tuple[str, ...]
    specialty: tuple[str, ...]
    topic_tags: tuple[str, ...] = Field(default_factory=tuple)
    license_status: LicenseStatus
    ai_usage_status: AiUsageStatus
    commercial_usage_status: CommercialUsageStatus
    content_ingestion_allowed: bool
    citation_required: bool
    clinical_review_status: ClinicalKnowledgeReviewStatus
    publication_date: date | None = None
    effective_date: date | None = None
    superseded_date: date | None = None
    supersedes_source_id: str | None = None
    license_type: str | None = None
    last_license_reviewed_at: datetime | None = None
    license_reviewed_by: str | None = None
    last_clinically_reviewed_at: datetime | None = None


class ClinicalRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    specialty_key: str
    topic_key: str
    rule_type: ClinicalRuleType
    status: ClinicalRuleStatus
    rule_version: str
    clinical_intent: str
    input_requirements: tuple[str, ...]
    trigger_conditions: dict[str, object]
    exclusion_conditions: dict[str, object]
    output_definition: dict[str, object]
    severity: ClinicalRuleSeverity
    priority: int
    explanation_key: str
    rationale_key: str
    source_refs: tuple[str, ...]
    guideline_refs: tuple[GuidelineRef, ...]
    evidence_refs: tuple[str, ...]
    clinical_review_status: ClinicalKnowledgeReviewStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    supersedes_rule_id: str | None = None
    superseded_by_rule_id: str | None = None
    change_reason: str | None = None


class ClinicalPolicyProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    profile_status: PolicyProfileStatus
    jurisdiction: str
    specialty_key: str
    preferred_guideline_families: tuple[str, ...]
    rule_set_version: str
    conflict_strategy: ConflictStrategy
    approved_by: str | None = None
    approved_at: datetime | None = None
    active_from: datetime | None = None
    active_until: datetime | None = None
