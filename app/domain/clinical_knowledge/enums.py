"""Enumerations for clinical knowledge registry and rule lifecycle."""

from enum import StrEnum


class ClinicalSourceType(StrEnum):
    GUIDELINE = "guideline"
    SOCIETY_STATEMENT = "society_statement"
    SYSTEMATIC_REVIEW = "systematic_review"
    PEER_REVIEWED_ARTICLE = "peer_reviewed_article"
    TEXTBOOK = "textbook"
    LICENSED_DATABASE = "licensed_database"
    REGULATORY_SOURCE = "regulatory_source"
    REIMBURSEMENT_SOURCE = "reimbursement_source"
    NATIONAL_GUIDELINE = "national_guideline"


class LicenseStatus(StrEnum):
    VERIFIED_OPEN = "verified_open"
    VERIFIED_COMMERCIAL_ALLOWED = "verified_commercial_allowed"
    LICENSED = "licensed"
    INTERNAL_REFERENCE_ONLY = "internal_reference_only"
    PERMISSION_REQUIRED = "permission_required"
    PROHIBITED_FOR_AI_INGESTION = "prohibited_for_ai_ingestion"
    UNKNOWN = "unknown"


class AiUsageStatus(StrEnum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class CommercialUsageStatus(StrEnum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class ClinicalKnowledgeReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class ClinicalRuleType(StrEnum):
    DIFFERENTIAL_SUPPORT = "differential_support"
    DIFFERENTIAL_AGAINST = "differential_against"
    NEXT_BEST_QUESTION = "next_best_question"
    MISSING_INFORMATION = "missing_information"
    SAFETY_ALERT = "safety_alert"
    RED_FLAG = "red_flag"
    WORKFLOW_GUARD = "workflow_guard"
    CONTRAINDICATION_CHECK = "contraindication_check"
    MEDICATION_SAFETY = "medication_safety"
    REIMBURSEMENT_CHECK = "reimbursement_check"


class ClinicalRuleStatus(StrEnum):
    DRAFT = "draft"
    SOURCE_LINKED = "source_linked"
    LICENSE_CLEARED = "license_cleared"
    CLINICAL_REVIEW = "clinical_review"
    APPROVED_DEMO = "approved_demo"
    APPROVED_PROD = "approved_prod"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ClinicalRuleSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class PolicyProfileStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ConflictStrategy(StrEnum):
    ADVISOR_CURATED_ONLY = "advisor_curated_only"
    PREFER_FIRST_FAMILY = "prefer_first_family"
    SHOW_BOTH_LABELED = "show_both_labeled"


LICENSE_STATUSES_ALLOWING_INGESTION = frozenset(
    {
        LicenseStatus.VERIFIED_OPEN,
        LicenseStatus.VERIFIED_COMMERCIAL_ALLOWED,
        LicenseStatus.LICENSED,
    }
)

LICENSE_STATUSES_ACCEPTABLE_FOR_PROD_RULE_CITATION = frozenset(
    {
        LicenseStatus.VERIFIED_OPEN,
        LicenseStatus.VERIFIED_COMMERCIAL_ALLOWED,
        LicenseStatus.LICENSED,
    }
)

KNOWN_SPECIALTY_KEYS = frozenset({"cardiology"})
