"""Clinical narrative v1 constants."""

NARRATIVE_VERSION = "llm_clinical_narrative_v1"
PROMPT_VERSION = "clinical_narrative_prompt_v1"
DEFAULT_OVERVIEW_QUERY = "patient clinical overview"
MAX_NARRATIVE_EVIDENCE = 10
DEFAULT_MAX_NARRATIVE_EVIDENCE = 8
MAX_QUERY_LENGTH = 512
DEFAULT_NARRATIVE_LANGUAGE = "tr"

CLINICAL_NARRATIVE_DISCLAIMER = (
    "This narrative is decision-support information generated from authorized clinical "
    "evidence only. It is not a medical diagnosis and does not replace professional "
    "clinical judgment."
)
