"""Port for validating clinical knowledge manifests."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RuleCatalogValidationIssue:
    """One validation failure with a stable code and human-readable message."""

    code: str
    message: str
    path: str | None = None


@dataclass
class RuleCatalogValidationResult:
    """Aggregate validation outcome."""

    issues: list[RuleCatalogValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


class RuleCatalogValidator(ABC):
    """Validate sources, rules, and policy profiles under a knowledge root."""

    @abstractmethod
    def validate_catalog(self, knowledge_root: Path) -> RuleCatalogValidationResult:
        """Run full catalog validation; fail closed on any issue."""
