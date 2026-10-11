"""Vocabulary eligibility modes for context assembly (not production engine policy)."""

from enum import StrEnum

from app.domain.clinical_vocabulary.enums import VocabularyItemStatus
from app.domain.clinical_vocabulary.models import ControlledVocabularyItem


class VocabularyEligibilityMode(StrEnum):
    """Which vocabulary term statuses may be referenced during assembly."""

    DEMO = "demo"
    PRODUCTION = "production"


def term_eligible_for_assembly(
    item: ControlledVocabularyItem,
    mode: VocabularyEligibilityMode,
) -> bool:
    if item.status in (VocabularyItemStatus.DEPRECATED, VocabularyItemStatus.RETIRED):
        return False
    if mode == VocabularyEligibilityMode.PRODUCTION:
        return item.engine_safe
    return item.status in (
        VocabularyItemStatus.APPROVED_DEMO,
        VocabularyItemStatus.APPROVED_PROD,
    )
