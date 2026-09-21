"""Canonical serialization and content hash tests."""

from datetime import UTC, datetime
from uuid import uuid4

from app.application.clinical_retrieval.canonical_serialization import build_canonical_text
from app.application.clinical_retrieval.content_hash import compute_content_hash
from app.application.dtos.clinical_evidence import ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient


def _bundle_with_record(diagnosis: str) -> tuple[ClinicalEvidenceBundle, ClinicalRetrievalDocumentDTO]:
    patient = Patient(owner_id=uuid4(), first_name="Secret", last_name="Person", date_of_birth=datetime(1990, 1, 1).date(), gender="male", phone="+1555")
    record_id = uuid4()
    record = MedicalRecord(
        owner_id=patient.owner_id,
        patient_id=patient.id,
        record_date=datetime(2026, 1, 1, tzinfo=UTC),
        record_type="visit",
        title="Visit",
        diagnosis=diagnosis,
    )
    record.id = record_id
    doc = ClinicalRetrievalDocumentDTO(
        evidence_id=f"medical_record:{record_id}",
        patient_id=patient.id,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=record_id,
        event_time=record.record_date,
    )
    bundle = ClinicalEvidenceBundle(patient=patient, medical_records=[record])
    return bundle, doc


def test_same_evidence_same_canonical_text_and_hash() -> None:
    bundle, doc = _bundle_with_record("Type 2 diabetes")
    t1 = build_canonical_text(doc, bundle)
    t2 = build_canonical_text(doc, bundle)
    assert t1 == t2
    assert compute_content_hash(t1) == compute_content_hash(t2)


def test_canonical_text_excludes_patient_demographics() -> None:
    bundle, doc = _bundle_with_record("Hypertension")
    text = build_canonical_text(doc, bundle)
    assert "Secret" not in text
    assert "Person" not in text
    assert "+1555" not in text
    assert "Hypertension" in text
