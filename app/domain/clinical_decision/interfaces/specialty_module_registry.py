"""Port for resolving specialty decision modules by specialty_key."""

from abc import ABC, abstractmethod

from app.domain.clinical_decision.interfaces.specialty_decision_module import SpecialtyDecisionModulePort


class SpecialtyDecisionModuleRegistryPort(ABC):
    """Register and resolve specialty modules in deterministic order."""

    @abstractmethod
    def register(self, module: SpecialtyDecisionModulePort) -> None:
        """Register one module; duplicate specialty_key must be rejected."""

    @abstractmethod
    def resolve(self, specialty_key: str) -> SpecialtyDecisionModulePort:
        """Return the module for a specialty or raise UnsupportedSpecialtyError."""

    @abstractmethod
    def list_specialty_keys(self) -> tuple[str, ...]:
        """Return registered specialty keys in sorted order."""
