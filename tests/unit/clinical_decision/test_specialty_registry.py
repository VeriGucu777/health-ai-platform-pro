"""Specialty module registry tests."""

import pytest

from app.application.clinical_decision.default_registry import build_default_specialty_registry
from app.application.clinical_decision.specialty.cardiology_no_rule import CardiologyNoRuleSpecialtyModule
from app.application.clinical_decision.specialty_registry import SpecialtyDecisionModuleRegistry
from app.domain.clinical_decision.exceptions import ClinicalDecisionValidationError, UnsupportedSpecialtyError


def test_default_registry_resolves_cardiology() -> None:
    registry = build_default_specialty_registry()
    module = registry.resolve("cardiology")
    assert module.specialty_key == "cardiology"
    assert registry.list_specialty_keys() == ("cardiology",)


def test_duplicate_registration_rejected() -> None:
    registry = SpecialtyDecisionModuleRegistry()
    registry.register(CardiologyNoRuleSpecialtyModule())
    with pytest.raises(ClinicalDecisionValidationError, match="duplicate"):
        registry.register(CardiologyNoRuleSpecialtyModule())


def test_unsupported_specialty_raises() -> None:
    registry = SpecialtyDecisionModuleRegistry()
    with pytest.raises(UnsupportedSpecialtyError):
        registry.resolve("cardiology")
