"""Enumerations for controlled clinical vocabulary (terminology only, not rules)."""

from enum import StrEnum


class VocabularyCategory(StrEnum):
    COMPLAINT = "complaint"
    FINDING = "finding"
    QUESTION = "question"
    ANSWER_CODE = "answer_code"
    VITAL = "vital"
    UNIT = "unit"
    ONSET = "onset"


class VocabularyItemStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_PENDING = "review_pending"
    APPROVED_DEMO = "approved_demo"
    APPROVED_PROD = "approved_prod"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class VocabularyClinicalReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    PROPOSED_BY_PRODUCT = "proposed_by_product"
    CLINICALLY_REVIEWED = "clinically_reviewed"
    CLINICALLY_APPROVED = "clinically_approved"


CARDIOLOGY_KEY_PREFIX = "card."
