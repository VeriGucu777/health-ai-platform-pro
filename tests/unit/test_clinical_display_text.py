"""Tests for internal operational note filtering."""

from app.application.clinical_display_text import (
    is_internal_operational_note,
    text_for_clinical_display,
)


def test_is_internal_operational_note_detects_seed_markers() -> None:
    assert is_internal_operational_note("seed:demo-enrich-a1/appt/00") is True
    assert is_internal_operational_note("  SEED:demo-enrich-a1  ") is True
    assert is_internal_operational_note("Follow-up visit notes") is False


def test_text_for_clinical_display_strips_internal_markers() -> None:
    assert text_for_clinical_display("seed:demo-enrich-a1/meas/01") is None
    assert text_for_clinical_display("Takip randevusu") == "Takip randevusu"
