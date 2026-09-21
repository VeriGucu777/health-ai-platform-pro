"""Build PHI-minimized evidence payloads from RAG retrieval results."""

from __future__ import annotations

from app.application.dtos.clinical_retrieval import ClinicalRetrievalResultDTO
from app.domain.interfaces.clinical_narrative_generator import ClinicalNarrativeEvidenceItem

_FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "first_name",
        "last_name",
        "full_name",
        "phone",
        "date_of_birth",
        "address",
        "email",
        "patient_name",
    },
)


def build_evidence_items(
    results: list[ClinicalRetrievalResultDTO],
    *,
    max_items: int,
) -> list[ClinicalNarrativeEvidenceItem]:
    """Map retrieval hits to LLM-safe evidence items."""
    items: list[ClinicalNarrativeEvidenceItem] = []
    for hit in results[:max_items]:
        clinical_text = _minimal_clinical_text(hit.content_fields)
        items.append(
            ClinicalNarrativeEvidenceItem(
                evidence_id=hit.evidence_id,
                source_type=hit.source_type.value,
                event_time_iso=hit.event_time.isoformat() if hit.event_time else None,
                clinical_text=clinical_text,
            ),
        )
    return items


def _minimal_clinical_text(content_fields: dict[str, str]) -> str:
    parts: list[str] = []
    for key, value in content_fields.items():
        normalized = key.strip().lower().replace("-", "_")
        if normalized in _FORBIDDEN_CONTENT_KEYS:
            continue
        cleaned = value.strip()
        if cleaned:
            parts.append(f"{normalized}: {cleaned}")
    return "; ".join(parts) if parts else "clinical content unavailable"
