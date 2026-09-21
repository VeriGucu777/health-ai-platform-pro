"""Deterministic post-generation guards for clinical narrative."""

from __future__ import annotations

import re

from app.application.clinical_narrative.exceptions import ClinicalNarrativeHallucinationError
from app.application.dtos.clinical_narrative import (
    ClinicalNarrativeFindingDTO,
    ClinicalNarrativeStructuredLLMOutput,
)
from app.domain.interfaces.clinical_narrative_generator import ClinicalNarrativeEvidenceItem

_MEDICATION_PATTERN = re.compile(
    r"\b(prescribe|prescription|take \d+ mg|start (?:patient on )?\w+|"
    r"augment with|initiate therapy|antibiotic course)\b",
    re.IGNORECASE,
)
_TREATMENT_PATTERN = re.compile(
    r"\b(recommend (?:surgery|procedure|treatment)|should undergo|must be treated with)\b",
    re.IGNORECASE,
)
_DIAGNOSIS_ASSERT_PATTERN = re.compile(
    r"\b(patient (?:has|is diagnosed with)|confirmed diagnosis|definitely has)\b",
    re.IGNORECASE,
)
_SCORE_IN_TEXT = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|score)\b", re.IGNORECASE)


class ClinicalNarrativeValidator:
    """Validate structured LLM output against evidence provenance."""

    def validate(
        self,
        output: ClinicalNarrativeStructuredLLMOutput,
        *,
        allowed_evidence_ids: set[str],
        evidence_items: list[ClinicalNarrativeEvidenceItem],
    ) -> None:
        self._validate_ids(output.source_evidence_ids, allowed_evidence_ids, label="source_evidence_ids")
        for section in (
            output.key_findings,
            output.risk_context,
            output.follow_up_context,
        ):
            for finding in section:
                self._validate_finding(finding, allowed_evidence_ids, evidence_items)

        combined_text = " ".join(
            [output.summary]
            + [f.text for f in output.key_findings]
            + [f.text for f in output.risk_context]
            + [f.text for f in output.follow_up_context]
        )
        self._guard_unsupported_clinical_claims(combined_text, evidence_items)

    def _validate_finding(
        self,
        finding: ClinicalNarrativeFindingDTO,
        allowed_ids: set[str],
        evidence_items: list[ClinicalNarrativeEvidenceItem],
    ) -> None:
        if not finding.source_evidence_ids:
            raise ClinicalNarrativeHallucinationError("Finding missing source_evidence_ids")
        self._validate_ids(finding.source_evidence_ids, allowed_ids, label="finding.source_evidence_ids")
        self._guard_unsupported_clinical_claims(finding.text, evidence_items)

    @staticmethod
    def _validate_ids(ids: list[str], allowed: set[str], *, label: str) -> None:
        for evidence_id in ids:
            if evidence_id not in allowed:
                raise ClinicalNarrativeHallucinationError(
                    f"Unknown evidence id in {label}",
                    details={"evidence_id": evidence_id},
                )

    def _guard_unsupported_clinical_claims(
        self,
        text: str,
        evidence_items: list[ClinicalNarrativeEvidenceItem],
    ) -> None:
        if _MEDICATION_PATTERN.search(text) and not self._evidence_mentions(text, evidence_items, _MEDICATION_PATTERN):
            raise ClinicalNarrativeHallucinationError("Unsupported medication recommendation")
        if _TREATMENT_PATTERN.search(text) and not self._evidence_mentions(text, evidence_items, _TREATMENT_PATTERN):
            raise ClinicalNarrativeHallucinationError("Unsupported treatment recommendation")
        if _DIAGNOSIS_ASSERT_PATTERN.search(text):
            raise ClinicalNarrativeHallucinationError("Unsupported definitive diagnosis language")

        evidence_blob = " ".join(item.clinical_text for item in evidence_items).lower()
        for match in _SCORE_IN_TEXT.finditer(text):
            token = match.group(1)
            if token not in evidence_blob and f"{token}%" not in evidence_blob:
                raise ClinicalNarrativeHallucinationError("Numeric risk/score not present in evidence")

    @staticmethod
    def _evidence_mentions(
        text: str,
        evidence_items: list[ClinicalNarrativeEvidenceItem],
        pattern: re.Pattern[str],
    ) -> bool:
        blob = " ".join(item.clinical_text for item in evidence_items)
        return bool(pattern.search(blob)) or bool(pattern.search(text) and pattern.search(blob))
