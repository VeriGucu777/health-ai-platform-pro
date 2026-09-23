"""Regression tests for seed-note filtering (user-visible PDF output rule)."""

from app.application.reports.report_i18n import patient_notes_for_report


def test_seed_prefixed_notes_are_excluded_from_report() -> None:
    assert patient_notes_for_report("seed:demo-live-policy-patient-v1") is None
    assert patient_notes_for_report("  SEED:test") is None
    assert patient_notes_for_report("demo-fixture:assigned-patient") is None
    assert patient_notes_for_report("internal-test:marker") is None


def test_clinical_notes_remain_available_for_report() -> None:
    assert patient_notes_for_report("Klinik takip notu") == "Klinik takip notu"
    assert patient_notes_for_report("  Alerji: lateks  ") == "Alerji: lateks"
