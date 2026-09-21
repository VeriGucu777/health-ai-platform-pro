"""Map structured LLM output and fallbacks to API DTOs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from app.application.clinical_narrative.constants import NARRATIVE_VERSION, PROMPT_VERSION
from app.application.dtos.clinical_narrative import (
    ClinicalNarrativeEvidenceReferenceDTO,
    ClinicalNarrativeStructuredLLMOutput,
    PatientClinicalNarrativeDTO,
)
from app.application.dtos.clinical_retrieval import ClinicalRetrievalResultDTO
from app.application.dtos.patient_clinical_summary import PatientClinicalSummaryDTO


def evidence_references_from_retrieval(
    results: list[ClinicalRetrievalResultDTO],
) -> list[ClinicalNarrativeEvidenceReferenceDTO]:
    return [
        ClinicalNarrativeEvidenceReferenceDTO(
            evidence_id=hit.evidence_id,
            source_type=hit.source_type,
            source_id=hit.source_id,
            event_time=hit.event_time,
        )
        for hit in results
    ]


def map_structured_to_narrative(
    *,
    patient_id: UUID,
    language: Literal["tr", "en"],
    structured: ClinicalNarrativeStructuredLLMOutput,
    evidence_refs: list[ClinicalNarrativeEvidenceReferenceDTO],
    generated_at: datetime | None = None,
) -> PatientClinicalNarrativeDTO:
    sections: list[str] = [structured.summary.strip()]
    if structured.key_findings:
        sections.append(_format_findings("Key findings", structured.key_findings))
    if structured.risk_context:
        sections.append(_format_findings("Risk context", structured.risk_context))
    if structured.follow_up_context:
        sections.append(_format_findings("Follow-up context", structured.follow_up_context))
    if structured.uncertainties:
        sections.append("Uncertainties: " + "; ".join(structured.uncertainties))

    limitations: list[str] = []
    if not evidence_refs:
        limitations.append("No matching clinical evidence was retrieved for the requested scope.")

    return PatientClinicalNarrativeDTO(
        patient_id=patient_id,
        narrative_version=NARRATIVE_VERSION,
        generated_at=generated_at or datetime.now(UTC),
        narrative="\n\n".join(part for part in sections if part),
        evidence_references=evidence_refs,
        limitations=limitations,
        fallback_used=False,
        prompt_version=PROMPT_VERSION,
        language=language,
    )


def map_deterministic_summary_fallback(
    *,
    patient_id: UUID,
    language: Literal["tr", "en"],
    summary: PatientClinicalSummaryDTO,
    evidence_refs: list[ClinicalNarrativeEvidenceReferenceDTO],
    reason: str,
) -> PatientClinicalNarrativeDTO:
    narrative_parts = [f"Deterministic clinical summary ({summary.summary_version})."]
    if summary.clinical_items:
        narrative_parts.append(
            "Clinical items: "
            + "; ".join(f"{item.label}: {item.detail}" for item in summary.clinical_items[:5]),
        )
    if summary.care_flags:
        narrative_parts.append(
            "Care flags: " + "; ".join(flag.message for flag in summary.care_flags[:5]),
        )
    if summary.recent_measurements:
        narrative_parts.append(
            "Recent measurements: "
            + "; ".join(
                f"{m.metric_type} {m.value} {m.unit}" for m in summary.recent_measurements[:5]
            ),
        )

    limitations = [
        "Deterministic clinical summary fallback was used because LLM narrative generation "
        f"was unavailable or failed validation ({reason}).",
    ]
    if language == "tr":
        limitations.append("Fallback metni İngilizce/veri dilinden türetilmiş olabilir.")

    return PatientClinicalNarrativeDTO(
        patient_id=patient_id,
        narrative_version=NARRATIVE_VERSION,
        generated_at=summary.generated_at,
        narrative="\n\n".join(narrative_parts),
        evidence_references=evidence_refs,
        limitations=limitations,
        fallback_used=True,
        prompt_version=PROMPT_VERSION,
        language=language,
    )


def _format_findings(title: str, findings) -> str:
    lines = []
    for finding in findings:
        refs = ", ".join(finding.source_evidence_ids)
        lines.append(f"- {finding.text} [{refs}]")
    return f"{title}:\n" + "\n".join(lines)
