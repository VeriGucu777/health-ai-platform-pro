"""Clinical decision engine ports."""

from app.domain.clinical_decision.interfaces.clinical_decision_engine import ClinicalDecisionEnginePort
from app.domain.clinical_decision.interfaces.specialty_decision_module import SpecialtyDecisionModulePort

__all__ = ["ClinicalDecisionEnginePort", "SpecialtyDecisionModulePort"]
