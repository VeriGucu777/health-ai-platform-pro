"""Factory for the initial pilot specialty registry."""

from app.application.clinical_decision.specialty.cardiology_no_rule import CardiologyNoRuleSpecialtyModule
from app.application.clinical_decision.specialty_registry import SpecialtyDecisionModuleRegistry


def build_default_specialty_registry() -> SpecialtyDecisionModuleRegistry:
    """Register cardiology stub only (deterministic ordering via sorted keys)."""
    registry = SpecialtyDecisionModuleRegistry()
    registry.register(CardiologyNoRuleSpecialtyModule())
    return registry
