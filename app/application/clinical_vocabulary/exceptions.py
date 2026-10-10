"""Controlled vocabulary catalog errors."""


class ClinicalVocabularyLoadError(Exception):
    """Failed to load or parse a vocabulary manifest."""


class ClinicalVocabularyValidationError(Exception):
    """Semantic validation failed for a vocabulary catalog."""
