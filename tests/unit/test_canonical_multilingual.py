"""Canonical serialization preserves stored language (no translation)."""

import json
from datetime import UTC, date, datetime
from uuid import uuid4

from app.application.clinical_retrieval.canonical_serialization import build_canonical_text
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient


def test_turkish_diagnosis_preserved_in_canonical_json() -> None:
    patient = Patient(
        owner_id=uuid4(),
        first_name="Ayşe",
        last_name="Yılmaz",
        date_of_birth=date(1985, 5, 5),
        gender="female",
    )
    source_id = uuid4()
    diagnosis_tr = "Tip 2 diyabet, kan şekeri takibi"
    record = MedicalRecord(
        owner_id=patient.owner_id,
        patient_id=patient.id,
        record_date=datetime(2026, 3, 1, tzinfo=UTC),
        record_type="visit",
        title="Kontrol",
        diagnosis=diagnosis_tr,
    )
    record.id = source_id
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{source_id}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=source_id,
    )
    bundle = ClinicalEvidenceBundle(patient=patient, medical_records=[record], retrieval_documents=[doc])
    canonical = build_canonical_text(doc, bundle)
    payload = json.loads(canonical)
    assert payload["diagnosis"] == diagnosis_tr
    assert "Type 2 diabetes" not in canonical


def test_english_diagnosis_preserved_in_canonical_json() -> None:
    patient = Patient(
        owner_id=uuid4(),
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1985, 5, 5),
        gender="male",
    )
    source_id = uuid4()
    diagnosis_en = "Hypertension, blood pressure monitoring"
    record = MedicalRecord(
        owner_id=patient.owner_id,
        patient_id=patient.id,
        record_date=datetime(2026, 3, 1, tzinfo=UTC),
        record_type="visit",
        title="Follow-up",
        diagnosis=diagnosis_en,
    )
    record.id = source_id
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{source_id}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=source_id,
    )
    bundle = ClinicalEvidenceBundle(patient=patient, medical_records=[record], retrieval_documents=[doc])
    canonical = build_canonical_text(doc, bundle)
    assert diagnosis_en in canonical
