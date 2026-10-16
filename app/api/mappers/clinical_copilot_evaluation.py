"""Map Clinical Copilot evaluation application data to API responses."""

from __future__ import annotations

from app.api.schemas.clinical_copilot_evaluation import (
    ClinicalCopilotEvaluationResponse,
    ClinicalCopilotProvenanceResponse,
    MissingInformationItemResponse,
)
from app.application.services.clinical_copilot_evaluation_service import (
    ClinicalCopilotEvaluationResponseData,
)


def clinical_copilot_evaluation_response(
    data: ClinicalCopilotEvaluationResponseData,
) -> ClinicalCopilotEvaluationResponse:
    result = data.result
    snap = data.snapshot
    vocab = snap.vocabulary
    missing = [
        MissingInformationItemResponse(
            information_key=item.data_element_key,
            display_key=item.display_key,
            criticality=item.criticality.value,
            rationale_key=item.rationale_key,
        )
        for item in result.missing_information
    ]
    provenance = ClinicalCopilotProvenanceResponse(
        input_snapshot_id=snap.input_snapshot_id,
        context_schema_version=snap.context_schema_version,
        vocabulary_id=vocab.vocabulary_id if vocab else None,
        vocabulary_version=vocab.vocabulary_version if vocab else None,
        vocabulary_manifest_hash=vocab.manifest_hash if vocab else None,
        rule_manifest_hash=result.rule_set_manifest_hash,
        engine_version=result.engine_version,
        specialty_module_version=result.specialty_module_version,
        policy_profile_id=result.policy_profile_id,
        policy_profile_version=result.policy_profile_version,
        context_profile=data.context_profile,
        specialty_key=snap.specialty_key,
        evaluated_at=result.evaluated_at,
        rule_provenance=[],
    )
    return ClinicalCopilotEvaluationResponse(
        evaluation_id=result.evaluation_id,
        encounter_id=result.encounter_id,
        patient_id=data.patient_id,
        evaluation_status=result.evaluation_status,
        read_only=data.read_only,
        missing_information=missing,
        review_domain_status=[],
        documentation_reminders=[],
        provenance=provenance,
    )
