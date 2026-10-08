"""Production-active rule eligibility (approved_prod + effective window)."""

from datetime import UTC, datetime

from app.domain.clinical_knowledge.enums import (
    LICENSE_STATUSES_ACCEPTABLE_FOR_PROD_RULE_CITATION,
    ClinicalKnowledgeReviewStatus,
    ClinicalRuleStatus,
)
from app.domain.clinical_knowledge.models import ClinicalKnowledgeSource, ClinicalRule


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_rule_effective_at(rule: ClinicalRule, reference_at: datetime) -> bool:
    """Return whether the rule is within its effective window at reference_at."""
    ref = _normalize_utc(reference_at)
    if rule.effective_from is not None and ref < _normalize_utc(rule.effective_from):
        return False
    if rule.effective_until is not None and ref > _normalize_utc(rule.effective_until):
        return False
    return True


def is_production_eligible_rule(
    rule: ClinicalRule,
    *,
    reference_at: datetime,
    sources_by_id: dict[str, ClinicalKnowledgeSource],
) -> bool:
    """Strict production filter beyond raw status (fail-closed semantics for active lists)."""
    if rule.status != ClinicalRuleStatus.APPROVED_PROD:
        return False
    if rule.status in (ClinicalRuleStatus.DEPRECATED, ClinicalRuleStatus.RETIRED):
        return False
    if rule.clinical_review_status not in (
        ClinicalKnowledgeReviewStatus.REVIEWED,
        ClinicalKnowledgeReviewStatus.APPROVED,
    ):
        return False
    if rule.reviewed_by is None or rule.reviewed_at is None:
        return False
    if rule.approved_by is None or rule.approved_at is None:
        return False
    if not is_rule_effective_at(rule, reference_at):
        return False
    for ref in rule.source_refs:
        source = sources_by_id.get(ref)
        if source is None:
            return False
        if source.license_status not in LICENSE_STATUSES_ACCEPTABLE_FOR_PROD_RULE_CITATION:
            return False
    return True
