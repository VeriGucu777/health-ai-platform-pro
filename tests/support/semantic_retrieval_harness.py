"""Shared demo evidence texts for multilingual semantic retrieval smoke tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticEvidenceFixture:
    evidence_id: str
    text_tr: str
    text_en: str


GLUCOSE = SemanticEvidenceFixture(
    evidence_id="demo:glucose",
    text_tr=(
        "Demo kayıt: Tip 2 diyabet takibi, açlık kan şekeri yüksek, "
        "HbA1c izlemi ve metformin tedavisi."
    ),
    text_en=(
        "Demo record: Type 2 diabetes follow-up, fasting glucose elevated, "
        "HbA1c monitoring and metformin therapy."
    ),
)

BLOOD_PRESSURE = SemanticEvidenceFixture(
    evidence_id="demo:bp",
    text_tr=(
        "Demo kayıt: Hipertansiyon kontrolü, kan basıncı ölçümleri, "
        "nabız ve antihipertansif ilaç değerlendirmesi."
    ),
    text_en=(
        "Demo record: Hypertension follow-up, blood pressure readings, "
        "heart rate and antihypertensive medication review."
    ),
)

APPOINTMENT = SemanticEvidenceFixture(
    evidence_id="demo:appt",
    text_tr="Demo kayıt: Rutin klinik randevu planlama ve check-in.",
    text_en="Demo record: Routine clinic appointment scheduling and check-in.",
)

ALL_DEMO_EVIDENCE = (GLUCOSE, BLOOD_PRESSURE, APPOINTMENT)
