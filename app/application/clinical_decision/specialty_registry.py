"""In-memory specialty module registry."""

from app.domain.clinical_decision.exceptions import ClinicalDecisionValidationError, UnsupportedSpecialtyError
from app.domain.clinical_decision.interfaces.specialty_decision_module import SpecialtyDecisionModulePort
from app.domain.clinical_decision.interfaces.specialty_module_registry import SpecialtyDecisionModuleRegistryPort


class SpecialtyDecisionModuleRegistry(SpecialtyDecisionModuleRegistryPort):
    """Deterministic registry of specialty decision modules."""

    def __init__(self) -> None:
        self._modules: dict[str, SpecialtyDecisionModulePort] = {}

    def register(self, module: SpecialtyDecisionModulePort) -> None:
        key = module.specialty_key
        if key in self._modules:
            raise ClinicalDecisionValidationError(f"duplicate specialty module registration: {key!r}")
        self._modules[key] = module

    def resolve(self, specialty_key: str) -> SpecialtyDecisionModulePort:
        module = self._modules.get(specialty_key)
        if module is None:
            raise UnsupportedSpecialtyError(f"unsupported specialty_key: {specialty_key!r}")
        return module

    def list_specialty_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._modules.keys()))
