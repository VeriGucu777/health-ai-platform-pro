"""ORM metadata tests for clinical encounter persistence shell."""

from __future__ import annotations

from app.infrastructure.database.models import (
    ClinicalEncounterModel,
    EncounterComplaintModel,
    EncounterFinalSummaryModel,
    EncounterFindingModel,
    EncounterQuestionResponseModel,
    HealthMeasurementModel,
    MedicalRecordModel,
)


def _index_names(model: type) -> set[str]:
    return {idx.name for idx in model.__table__.indexes if idx.name}


def test_clinical_encounter_tables_registered() -> None:
    assert ClinicalEncounterModel.__tablename__ == "clinical_encounters"
    assert EncounterComplaintModel.__tablename__ == "encounter_complaints"
    assert EncounterFindingModel.__tablename__ == "encounter_findings"
    assert EncounterQuestionResponseModel.__tablename__ == "encounter_question_responses"
    assert EncounterFinalSummaryModel.__tablename__ == "encounter_final_summaries"


def test_clinical_encounter_partial_unique_indexes() -> None:
    names = _index_names(ClinicalEncounterModel)
    assert "uq_clinical_encounters_one_active_per_patient_org" in names
    assert "uq_clinical_encounters_appointment_id" in names


def test_child_partial_unique_indexes() -> None:
    assert "uq_encounter_complaints_one_primary_active" in _index_names(EncounterComplaintModel)
    assert "uq_encounter_question_responses_active_key" in _index_names(
        EncounterQuestionResponseModel,
    )


def test_version_check_constraint_present() -> None:
    assert "ck_clinical_encounters_version_gte_1" in {
        c.name for c in ClinicalEncounterModel.__table__.constraints
    }


def test_measurement_and_record_encounter_id_nullable() -> None:
    assert "encounter_id" in HealthMeasurementModel.__table__.columns
    assert HealthMeasurementModel.__table__.columns["encounter_id"].nullable is True
    assert "encounter_id" in MedicalRecordModel.__table__.columns
    assert MedicalRecordModel.__table__.columns["encounter_id"].nullable is True


def test_encounter_fks_use_restrict_not_cascade_on_aggregate() -> None:
    table = EncounterComplaintModel.__table__
    fks = {fk.parent.name: fk.ondelete for fk in table.foreign_keys}
    assert fks["encounter_id"] == "RESTRICT"


def test_final_summary_unique_encounter_id() -> None:
    assert EncounterFinalSummaryModel.__table__.columns["encounter_id"].unique is True
