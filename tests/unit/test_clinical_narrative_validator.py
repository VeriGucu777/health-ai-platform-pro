"""Clinical narrative provenance validator tests."""

import pytest

from app.application.clinical_narrative.exceptions import ClinicalNarrativeHallucinationError
from app.application.clinical_narrative.validator import ClinicalNarrativeValidator
from app.application.dtos.clinical_narrative import (
    ClinicalNarrativeFindingDTO,
    ClinicalNarrativeStructuredLLMOutput,
)
from app.domain.interfaces.clinical_narrative_generator import ClinicalNarrativeEvidenceItem


def test_validator_rejects_unknown_evidence_id() -> None:
    output = ClinicalNarrativeStructuredLLMOutput(
        summary="Summary",
        key_findings=[
            ClinicalNarrativeFindingDTO(
                text="Finding",
                source_evidence_ids=["medical_record:00000000-0000-0000-0000-000000000099"],
            ),
        ],
        source_evidence_ids=["medical_record:00000000-0000-0000-0000-000000000099"],
    )
    evidence = [
        ClinicalNarrativeEvidenceItem(
            evidence_id="medical_record:11111111-1111-1111-1111-111111111111",
            source_type="medical_record",
            event_time_iso=None,
            clinical_text="diagnosis: diabetes",
        ),
    ]
    with pytest.raises(ClinicalNarrativeHallucinationError):
        ClinicalNarrativeValidator().validate(
            output,
            allowed_evidence_ids={evidence[0].evidence_id},
            evidence_items=evidence,
        )


def test_validator_rejects_unsupported_medication_recommendation() -> None:
    eid = "medical_record:11111111-1111-1111-1111-111111111111"
    evidence = [
        ClinicalNarrativeEvidenceItem(
            evidence_id=eid,
            source_type="medical_record",
            event_time_iso=None,
            clinical_text="diagnosis: diabetes monitoring",
        ),
    ]
    output = ClinicalNarrativeStructuredLLMOutput(
        summary="Prescribe 500mg metformin daily",
        key_findings=[ClinicalNarrativeFindingDTO(text="Prescribe 500mg metformin daily", source_evidence_ids=[eid])],
        source_evidence_ids=[eid],
    )
    with pytest.raises(ClinicalNarrativeHallucinationError):
        ClinicalNarrativeValidator().validate(
            output,
            allowed_evidence_ids={eid},
            evidence_items=evidence,
        )
