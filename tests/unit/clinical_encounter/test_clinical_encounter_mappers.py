"""Mapper unit tests for clinical encounter persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.clinical_encounter.entities import (
    ClinicalEncounter,
    ClinicalEncounterAggregate,
    EncounterComplaint,
    EncounterFinalSummary,
    EncounterFinding,
    EncounterQuestionResponse,
    EncounterSummarySection,
)
from app.domain.clinical_encounter.enums import (
    ClinicalInputSource,
    EncounterStatus,
    FindingType,
    QuestionAnswerType,
)
from app.infrastructure.clinical_encounter.exceptions import ClinicalEncounterMappingError
from app.infrastructure.clinical_encounter.mappers import (
    build_aggregate,
    complaint_domain_to_model,
    complaint_model_to_domain,
    encounter_domain_to_model,
    encounter_model_to_domain,
    final_summary_domain_to_model,
    final_summary_model_to_domain,
    summary_sections_to_json,
)
from app.infrastructure.database.models.clinical_encounter import (
    ClinicalEncounterModel,
    EncounterComplaintModel,
    EncounterFinalSummaryModel,
)


def _encounter() -> ClinicalEncounter:
    return ClinicalEncounter(
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        status=EncounterStatus.DRAFT,
        locale="en",
    )


def test_encounter_round_trip() -> None:
    entity = _encounter()
    model = encounter_domain_to_model(entity)
    back = encounter_model_to_domain(model)
    assert back.id == entity.id
    assert back.specialty_key == "cardiology"
    assert back.status == EncounterStatus.DRAFT


def test_complaint_round_trip_preserves_display_text_field() -> None:
    enc_id = uuid4()
    clinician = uuid4()
    entity = EncounterComplaint(
        encounter_id=enc_id,
        clinician_display_text="display only",
        sequence_no=1,
        recorded_by=clinician,
    )
    model = complaint_domain_to_model(entity)
    back = complaint_model_to_domain(model)
    assert back.clinician_display_text == "display only"
    assert "display only" not in repr(back)


def test_final_summary_json_validation_fail_closed() -> None:
    model = EncounterFinalSummaryModel(
        id=uuid4(),
        encounter_id=uuid4(),
        summary_version=1,
        summary_sections={"bad": "shape"},
        finalized_by=uuid4(),
        finalized_at=datetime.now(UTC),
    )
    with pytest.raises(ClinicalEncounterMappingError):
        final_summary_model_to_domain(model)


def test_final_summary_sections_round_trip() -> None:
    enc_id = uuid4()
    section = EncounterSummarySection(section_key="plan", content_key="generic.plan")
    summary = EncounterFinalSummary.create(
        encounter_id=enc_id,
        summary_version=1,
        summary_sections=(section,),
        clinician_note=None,
        finalized_by=uuid4(),
        finalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    model = final_summary_domain_to_model(summary)
    assert summary_sections_to_json(summary.summary_sections) == model.summary_sections
    back = final_summary_model_to_domain(model)
    assert back.summary_sections[0].section_key == "plan"


def test_build_aggregate_orders_from_sorted_inputs() -> None:
    enc = ClinicalEncounterModel(
        id=uuid4(),
        patient_id=uuid4(),
        organization_id=uuid4(),
        clinician_user_id=uuid4(),
        specialty_key="cardiology",
        status="draft",
        locale="en",
        version=1,
        is_active=True,
    )
    c1 = EncounterComplaintModel(
        id=uuid4(),
        encounter_id=enc.id,
        complaint_key="a",
        sequence_no=2,
        recorded_at=datetime.now(UTC),
        recorded_by=uuid4(),
        is_primary=False,
        negated=False,
        is_active=True,
    )
    c2 = EncounterComplaintModel(
        id=uuid4(),
        encounter_id=enc.id,
        complaint_key="b",
        sequence_no=1,
        recorded_at=datetime.now(UTC),
        recorded_by=uuid4(),
        is_primary=True,
        negated=False,
        is_active=True,
    )
    agg = build_aggregate(enc, complaints=[c2, c1], findings=[], responses=[], final_summary=None)
    assert [c.sequence_no for c in agg.complaints] == [1, 2]
