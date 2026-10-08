"""Port for resolving active clinical policy profiles (future runtime wiring)."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class PolicyProfileSnapshot(BaseModel):
    """Evaluation-time policy metadata; draft profiles must not appear as production-active."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    profile_version: str
    is_production_active: bool = False


class ClinicalPolicyProfileResolverPort(ABC):
    """Resolve which policy profile governs guideline conflict handling."""

    @abstractmethod
    def resolve_for_evaluation(self) -> PolicyProfileSnapshot:
        """Return the policy snapshot bound to the current evaluation environment."""
