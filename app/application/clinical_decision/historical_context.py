"""Map authorized clinical evidence into engine-safe historical context summaries."""

from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.domain.clinical_decision.models import EncounterHistoricalContext


def encounter_historical_context_from_bundle(
    bundle: ClinicalEvidenceBundle | None,
) -> EncounterHistoricalContext | None:
    """Build a PHI-minimized history slice; does not copy record text into the engine context."""
    if bundle is None:
        return None
    return EncounterHistoricalContext(
        has_measurements=bool(bundle.health_measurements),
        has_medical_records=bool(bundle.medical_records),
        has_risk_history=bool(bundle.risk_assessment_history),
        has_appointments=bool(bundle.appointments),
    )
