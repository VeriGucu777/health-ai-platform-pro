"""Map raw manifest dicts to domain models."""

from typing import Any

from app.domain.clinical_knowledge.models import (
    ClinicalKnowledgeSource,
    ClinicalPolicyProfile,
    ClinicalRule,
    GuidelineRef,
)


def _tuple_str(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a list")
    return tuple(str(item) for item in value)


def source_from_dict(data: dict[str, Any]) -> ClinicalKnowledgeSource:
    return ClinicalKnowledgeSource(
        source_id=str(data["source_id"]),
        source_type=data["source_type"],
        title=str(data["title"]),
        publisher_or_organization=str(data["publisher_or_organization"]),
        edition_or_version=str(data["edition_or_version"]),
        publication_year=int(data["publication_year"]),
        official_url=str(data["official_url"]),
        jurisdiction=_tuple_str(data["jurisdiction"], "jurisdiction"),
        specialty=_tuple_str(data["specialty"], "specialty"),
        topic_tags=_tuple_str(data.get("topic_tags") or [], "topic_tags"),
        license_status=data["license_status"],
        ai_usage_status=data["ai_usage_status"],
        commercial_usage_status=data["commercial_usage_status"],
        content_ingestion_allowed=bool(data["content_ingestion_allowed"]),
        citation_required=bool(data["citation_required"]),
        clinical_review_status=data["clinical_review_status"],
        publication_date=data.get("publication_date"),
        effective_date=data.get("effective_date"),
        superseded_date=data.get("superseded_date"),
        supersedes_source_id=data.get("supersedes_source_id"),
        license_type=data.get("license_type"),
        last_license_reviewed_at=data.get("last_license_reviewed_at"),
        license_reviewed_by=data.get("license_reviewed_by"),
        last_clinically_reviewed_at=data.get("last_clinically_reviewed_at"),
    )


def rule_from_dict(data: dict[str, Any]) -> ClinicalRule:
    guideline_refs_raw = data.get("guideline_refs") or []
    guideline_refs = tuple(
        GuidelineRef.model_validate(ref) for ref in guideline_refs_raw if isinstance(ref, dict)
    )
    return ClinicalRule(
        rule_id=str(data["rule_id"]),
        specialty_key=str(data["specialty_key"]),
        topic_key=str(data["topic_key"]),
        rule_type=data["rule_type"],
        status=data["status"],
        rule_version=str(data["rule_version"]),
        clinical_intent=str(data["clinical_intent"]),
        input_requirements=_tuple_str(data.get("input_requirements") or [], "input_requirements"),
        trigger_conditions=dict(data.get("trigger_conditions") or {}),
        exclusion_conditions=dict(data.get("exclusion_conditions") or {}),
        output_definition=dict(data.get("output_definition") or {}),
        severity=data["severity"],
        priority=int(data["priority"]),
        explanation_key=str(data["explanation_key"]),
        rationale_key=str(data["rationale_key"]),
        source_refs=_tuple_str(data.get("source_refs") or [], "source_refs"),
        guideline_refs=guideline_refs,
        evidence_refs=_tuple_str(data.get("evidence_refs") or [], "evidence_refs"),
        clinical_review_status=data["clinical_review_status"],
        reviewed_by=data.get("reviewed_by"),
        reviewed_at=data.get("reviewed_at"),
        approved_by=data.get("approved_by"),
        approved_at=data.get("approved_at"),
        effective_from=data.get("effective_from"),
        effective_until=data.get("effective_until"),
        supersedes_rule_id=data.get("supersedes_rule_id"),
        superseded_by_rule_id=data.get("superseded_by_rule_id"),
        change_reason=data.get("change_reason"),
    )


def policy_profile_from_dict(data: dict[str, Any]) -> ClinicalPolicyProfile:
    return ClinicalPolicyProfile(
        profile_id=str(data["profile_id"]),
        profile_status=data["profile_status"],
        jurisdiction=str(data["jurisdiction"]),
        specialty_key=str(data["specialty_key"]),
        preferred_guideline_families=_tuple_str(
            data["preferred_guideline_families"],
            "preferred_guideline_families",
        ),
        rule_set_version=str(data["rule_set_version"]),
        conflict_strategy=data["conflict_strategy"],
        approved_by=data.get("approved_by"),
        approved_at=data.get("approved_at"),
        active_from=data.get("active_from"),
        active_until=data.get("active_until"),
    )
