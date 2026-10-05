"""Tests for marker-scoped legacy demo enrichment cleanup tooling."""

from __future__ import annotations

from datetime import UTC, datetime
import pytest

from app.application.seeding.demo_clinical_enrichment import PATIENT_SPECS
from app.domain.risk.enums import RULE_BASED_MODEL_KIND
from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.application.seeding.demo_enrichment_legacy_cleanup import (
    EXPECTED_LEGACY_MEASUREMENTS_BY_KEY,
    EXPECTED_LEGACY_MEDICAL_RECORDS_BY_KEY,
    EXPECTED_PRODUCTION_PATIENT_IDS,
    DemoEnrichmentLegacyCleanupConfig,
    LegacyCleanupInventory,
    PatientLegacyInventory,
    classify_measurement_notes,
    classify_medical_record_notes,
    run_demo_enrichment_legacy_cleanup,
    validate_pre_cleanup_guards,
)
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import Organization, PatientAssignment
from app.domain.organization.enums import AssignmentStatus
from app.domain.risk.enums import RiskAssessmentType
from tests.support.memory_appointment_repository import InMemoryAppointmentRepository
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_consent_repository import InMemoryPatientConsentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_risk_assessment_history_repository import (
    InMemoryRiskAssessmentHistoryRepository,
)
from tests.support.memory_user_repository import InMemoryUserRepository


def test_classify_legacy_measurement_notes():
    assert classify_measurement_notes("seed:demo-enrich-a1/meas/00") == "legacy_active"
    assert classify_measurement_notes("seed:demo-enrich-b2/meas/04") == "legacy_active"
    assert classify_measurement_notes("seed:demo-enrich-a1/meas/v2/00") == "v2"
    assert (
        classify_measurement_notes("seed:demo-enrich-a1/meas/00", is_active=False)
        == "legacy_deactivated"
    )
    assert classify_measurement_notes("seed:demo-enrich-a1/appt/00") == "non_task3"
    assert classify_measurement_notes(None) == "unrelated"


def test_classify_legacy_medical_record_notes():
    assert classify_medical_record_notes("seed:demo-enrich-a1/record/01") == "legacy_active"
    assert classify_medical_record_notes("seed:demo-enrich-a2/record/v2/00") == "v2"
    assert classify_medical_record_notes("manual clinic note") == "unrelated"


def test_validate_guard_aborts_wrong_total():
    rows = [
        PatientLegacyInventory(
            patient_key="a1",
            patient_id=EXPECTED_PRODUCTION_PATIENT_IDS["a1"],
            marker_ok=True,
            legacy_measurements_active=4,
            legacy_medical_records_active=2,
        ),
    ]
    inv = LegacyCleanupInventory(patient_rows=rows)
    guard = validate_pre_cleanup_guards(inv, strict_production_ids=True)
    assert not guard.ok
    assert guard.abort_reasons


async def _legacy_fixture_repos(*, wrong_meas_count: bool = False, with_v2: bool = False, unmarked: bool = False):
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)
    measurements = InMemoryHealthMeasurementRepository()
    records = InMemoryMedicalRecordRepository()
    appointments = InMemoryAppointmentRepository()
    risk = InMemoryRiskAssessmentHistoryRepository()
    consents = InMemoryPatientConsentRepository()

    org = await orgs.create(
        Organization(name="Demo Live Policy Clinic", slug=DEMO_ORGANIZATION_SLUG, is_active=True),
    )
    doctor = await users.create(
        User(
            email="cleanup-doctor@example.com",
            hashed_password="x",
            first_name="Doc",
            last_name="One",
            role=UserRole.DOCTOR,
            is_verified=True,
        ),
    )
    now = datetime.now(UTC)
    for spec in PATIENT_SPECS:
        if spec.key not in EXPECTED_PRODUCTION_PATIENT_IDS:
            continue
        patient_id = EXPECTED_PRODUCTION_PATIENT_IDS[spec.key]
        patient = await patients.create(
            Patient(
                id=patient_id,
                owner_id=doctor.id,
                organization_id=org.id,
                first_name=spec.first_name,
                last_name=spec.last_name,
                date_of_birth=spec.date_of_birth,
                gender=spec.gender,
                notes=spec.marker,
                is_active=True,
            ),
        )
        meas_total = EXPECTED_LEGACY_MEASUREMENTS_BY_KEY[spec.key]
        if wrong_meas_count and spec.key == "a1":
            meas_total -= 1
        for idx in range(meas_total):
            await measurements.create(
                HealthMeasurement(
                    owner_id=doctor.id,
                    patient_id=patient.id,
                    measured_at=now,
                    notes=f"{spec.marker}/meas/{idx:02d}",
                ),
            )
        if with_v2 and spec.key == "a1":
            await measurements.create(
                HealthMeasurement(
                    owner_id=doctor.id,
                    patient_id=patient.id,
                    measured_at=now,
                    notes=f"{spec.marker}/meas/v2/00",
                ),
            )
        if unmarked and spec.key == "a1":
            await measurements.create(
                HealthMeasurement(
                    owner_id=doctor.id,
                    patient_id=patient.id,
                    measured_at=now,
                    notes=None,
                ),
            )
        for idx in range(EXPECTED_LEGACY_MEDICAL_RECORDS_BY_KEY[spec.key]):
            await records.create(
                MedicalRecord(
                    owner_id=doctor.id,
                    patient_id=patient.id,
                    record_date=now,
                    record_type="visit",
                    title="demo",
                    notes=f"{spec.marker}/record/{idx:02d}",
                ),
            )
        await appointments.create(
            Appointment(
                owner_id=doctor.id,
                patient_id=patient.id,
                appointment_date=now,
                appointment_type="follow_up",
                status="scheduled",
                notes=f"{spec.marker}/appt/00",
            ),
        )
        await assignments.create(
            PatientAssignment(
                patient_id=patient.id,
                organization_id=org.id,
                assignee_user_id=doctor.id,
                status=AssignmentStatus.ACTIVE,
            ),
        )
        if spec.key == "a1":
            for _ in range(3):
                await risk.append(
                    RiskAssessmentHistory(
                        patient_id=patient.id,
                        organization_id=org.id,
                        assessment_type=RiskAssessmentType.DIABETES,
                        assessment_status="completed",
                        model_kind=RULE_BASED_MODEL_KIND,
                        model_version="rule_based_v1",
                        evaluated_by_user_id=doctor.id,
                        evaluated_at=now,
                        result_snapshot={"seed_marker": f"{spec.marker}/risk/primary"},
                    ),
                )

    return orgs, org, doctor, patients, measurements, records, appointments, risk, assignments, consents


@pytest.mark.asyncio
async def test_dry_run_no_mutation():
    org_repo, _org, doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos()
    )

    before = await measurements.list_by_owner(doctor.id, limit=500)
    result = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=False,
    )
    after = await measurements.list_by_owner(doctor.id, limit=500)
    assert result.guard.ok
    assert result.inventory.legacy_measurements_active == 18
    assert before[0].notes == after[0].notes
    assert not result.mutated


@pytest.mark.asyncio
async def test_confirm_cleanup_deactivates_legacy_only():
    org_repo, _org, doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos()
    )

    appt_before = len(await appointments.list_by_owner(doctor.id, limit=500))
    risk_before = await risk.count_by_patient(EXPECTED_PRODUCTION_PATIENT_IDS["a1"])

    result = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=True,
    )
    assert result.mutated
    assert result.post_verify_ok
    assert result.deactivated_measurements == 18
    assert result.deactivated_medical_records == 7
    assert result.inventory.legacy_measurements_active == 0
    stored = await measurements.list_by_owner(doctor.id, limit=500, include_inactive=True)
    assert all(not row.is_active for row in stored if "meas/" in (row.notes or ""))
    assert all("legacy-deactivated" not in (row.notes or "") for row in stored)
    assert appt_before == len(await appointments.list_by_owner(doctor.id, limit=500))
    assert risk_before == await risk.count_by_patient(EXPECTED_PRODUCTION_PATIENT_IDS["a1"])


@pytest.mark.asyncio
async def test_wrong_count_aborts_no_mutation():
    org_repo, _org, _doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos(wrong_meas_count=True)
    )

    result = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=True,
    )
    assert result.mode == "cleanup_aborted"
    assert not result.mutated
    assert any("legacy measurements" in r for r in result.abort_reasons)


@pytest.mark.asyncio
async def test_v2_present_aborts():
    org_repo, _org, _doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos(with_v2=True)
    )

    result = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=True,
    )
    assert not result.mutated
    assert any("v2 measurements" in r for r in result.abort_reasons)


@pytest.mark.asyncio
async def test_unmarked_measurement_aborts():
    org_repo, _org, _doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos(unmarked=True)
    )

    analyze = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=False,
    )
    assert analyze.inventory.non_task3_measurements >= 1
    assert not analyze.guard.ok


@pytest.mark.asyncio
async def test_idempotent_second_analyze_after_cleanup():
    org_repo, _org, _doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos()
    )

    first = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=True,
    )
    assert first.post_verify_ok
    second = await run_demo_enrichment_legacy_cleanup(
        organization_repository=org_repo,
        patient_repository=patients,
        measurement_repository=measurements,
        medical_record_repository=records,
        appointment_repository=appointments,
        risk_history_repository=risk,
        assignment_repository=assignments,
        consent_repository=consents,
        config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
        confirm_cleanup=False,
    )
    assert second.inventory.legacy_measurements_active == 0
    assert not second.guard.ok


@pytest.mark.asyncio
async def test_transaction_rollback_on_update_failure():
    org_repo, _org, doctor, patients, measurements, records, appointments, risk, assignments, consents = (
        await _legacy_fixture_repos()
    )

    original_update = measurements.update
    calls = {"n": 0}

    async def flaky_update(entity):
        calls["n"] += 1
        if calls["n"] > 2:
            raise RuntimeError("simulated failure")
        return await original_update(entity)

    measurements.update = flaky_update  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await run_demo_enrichment_legacy_cleanup(
            organization_repository=org_repo,
            patient_repository=patients,
            measurement_repository=measurements,
            medical_record_repository=records,
            appointment_repository=appointments,
            risk_history_repository=risk,
            assignment_repository=assignments,
            consent_repository=consents,
            config=DemoEnrichmentLegacyCleanupConfig(verify_production_patient_ids=True),
            confirm_cleanup=True,
        )

    active = [
        row
        for row in await measurements.list_by_owner(doctor.id, limit=500)
        if classify_measurement_notes(row.notes) == "legacy_active"
    ]
    assert len(active) > 0
