"""Historical context assembly from clinical evidence bundle."""

from datetime import date
from uuid import uuid4

from app.application.clinical_decision.historical_context import (
    encounter_historical_context_from_bundle,
)
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.patient import Patient


def test_bundle_maps_to_summary_flags_only() -> None:
    patient = Patient(
        id=uuid4(),
        owner_id=uuid4(),
        first_name="Synthetic",
        last_name="Patient",
        date_of_birth=date(1980, 1, 1),
        gender="female",
        is_active=True,
    )
    bundle = ClinicalEvidenceBundle(
        patient=patient,
        health_measurements=[
            HealthMeasurement(
                id=uuid4(),
                owner_id=patient.owner_id,
                patient_id=patient.id,
                measured_at=patient.created_at,
            ),
        ],
    )
    hist = encounter_historical_context_from_bundle(bundle)
    assert hist is not None
    assert hist.has_measurements is True
    assert hist.has_medical_records is False
