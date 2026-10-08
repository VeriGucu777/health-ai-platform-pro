"""Clinical knowledge catalog load and validation errors."""


class ClinicalKnowledgeCatalogError(Exception):
    """Base error for clinical knowledge catalog operations."""


class ClinicalKnowledgeCatalogLoadError(ClinicalKnowledgeCatalogError):
    """Manifest or filesystem load failed."""


class ClinicalKnowledgeCatalogValidationError(ClinicalKnowledgeCatalogError):
    """Full-catalog validation failed (fail-closed)."""

    def __init__(self, message: str, *, issues: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues


class ClinicalKnowledgeCatalogIntegrityError(ClinicalKnowledgeCatalogError):
    """Catalog integrity or path safety violation."""
