"""Port for deterministic clinical decision evaluation."""

from abc import ABC, abstractmethod

from app.domain.clinical_decision.models import (
    ClinicalDecisionEvaluationResult,
    EncounterEvaluationContext,
)


class ClinicalDecisionEnginePort(ABC):
    """Evaluate encounter context into decision-support outputs (side-effect free)."""

    @property
    @abstractmethod
    def engine_version(self) -> str:
        """Stable engine implementation version."""

    @property
    @abstractmethod
    def specialty_module_version(self) -> str:
        """Active specialty module version, or explicit none placeholder."""

    @abstractmethod
    def evaluate(self, context: EncounterEvaluationContext) -> ClinicalDecisionEvaluationResult:
        """Produce a versioned evaluation result from structured encounter input."""
