"""Unit tests for demo clinical enrichment seed."""

import pytest

from app.application.seeding.demo_clinical_enrichment import (
    ENRICHMENT_MARKERS,
    DemoClinicalEnrichmentConfig,
    analyze_demo_clinical_enrichment,
    seed_demo_clinical_enrichment,
)
from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.core.security import hash_password
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import Organization, OrganizationMembership
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole
from app.domain.risk.enums import RiskAssessmentType
from tests.support.clinical_read_service_factory import (
    build_clinical_timeline_service,
    build_patient_health_report_service,
)
from tests.support.patient_service_factory import build_policy_patient_service
from tests.support.memory_appointment_repository import InMemoryAppointmentRepository
from tests.support.memory_health_measurement_repository import InMemoryHealthMeasurementRepository
from tests.support.memory_medical_record_repository import InMemoryMedicalRecordRepository
from tests.support.memory_organization_membership_repository import (
    InMemoryOrganizationMembershipRepository,
)
from tests.support.memory_organization_repository import InMemoryOrganizationRepository
from tests.support.memory_patient_assignment_repository import InMemoryPatientAssignmentRepository
from tests.support.memory_patient_consent_repository import InMemoryPatientConsentRepository
from tests.support.memory_patient_repository import InMemoryPatientRepository
from tests.support.memory_risk_assessment_history_repository import (
    InMemoryRiskAssessmentHistoryRepository,
)
from tests.support.memory_user_repository import InMemoryUserRepository
async def _base_repos():
    users = InMemoryUserRepository()
    orgs = InMemoryOrganizationRepository()
    memberships = InMemoryOrganizationMembershipRepository()
    assignments = InMemoryPatientAssignmentRepository()
    patients = InMemoryPatientRepository(assignment_repository=assignments)
    consents = InMemoryPatientConsentRepository()
    measurements = InMemoryHealthMeasurementRepository()
    records = InMemoryMedicalRecordRepository()
    appointments = InMemoryAppointmentRepository()
    risk = InMemoryRiskAssessmentHistoryRepository()
    return users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk


async def _seed_org_admin_doctor_a(users, orgs, memberships):
    org = await orgs.create(
        Organization(name="Demo Live Policy Clinic", slug=DEMO_ORGANIZATION_SLUG, is_active=True),
    )
    admin = await users.create(
        User(
            email="enrich-admin@example.com",
            hashed_password=hash_password("AdminPass12345!"),
            first_name="Clinic",
            last_name="Admin",
            role=UserRole.CLINIC_ADMIN,
            is_verified=True,
        ),
    )
    doctor_a = await users.create(
        User(
            email="enrich-doctor-a@example.com",
            hashed_password=hash_password("DoctorAPass12345!"),
            first_name="Demo",
            last_name="Doctor One",
            role=UserRole.DOCTOR,
            is_verified=True,
        ),
    )
    await memberships.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    return org, admin, doctor_a


def _enrichment_kwargs(
    users,
    orgs,
    memberships,
    patients,
    assignments,
    consents,
    measurements,
    records,
    appointments,
    risk,
    *,
    admin_email: str,
    doctor_a_email: str,
    doctor_b_email: str,
    doctor_b_password: str,
):
    return {
        "user_repository": users,
        "organization_repository": orgs,
        "membership_repository": memberships,
        "patient_repository": patients,
        "assignment_repository": assignments,
        "consent_repository": consents,
        "measurement_repository": measurements,
        "medical_record_repository": records,
        "appointment_repository": appointments,
        "risk_history_repository": risk,
        "config": DemoClinicalEnrichmentConfig(
            clinic_admin_email=admin_email,
            doctor_a_email=doctor_a_email,
            doctor_b_email=doctor_b_email,
            doctor_b_password=doctor_b_password,
        ),
    }


@pytest.mark.asyncio
async def test_enrichment_first_run_creates_four_patients_and_clinical_rows() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    assert result.doctor_b_user_id is not None
    assert result.doctor_a_user_id != result.doctor_b_user_id
    assert result.doctor_b_status == "doctor_b_ready"
    assert len(result.patient_ids) == 5
    assert all(result.created_patients.get(k) for k in ("a1", "a2", "a3", "b1", "b2"))
    for key in ("a1", "a2", "a3", "b1", "b2"):
        counts = result.counts[key]
        assert counts.measurements >= 3
        assert counts.medical_records >= 1
        assert counts.appointments >= 1
        assert counts.risk_history >= 1
        assert counts.consent_granted is True
        assert counts.assignment_active is True


@pytest.mark.asyncio
async def test_enrichment_second_run_is_idempotent() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    first = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    second = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    assert len(first.patient_ids) == len(second.patient_ids) == 5
    assert all(
        second.created_patients.get(k) is False for k in ("a1", "a2", "a3", "b1", "b2")
    )
    for key in ("a1", "a2", "a3", "b1", "b2"):
        assert first.counts[key].measurements == second.counts[key].measurements
        assert first.counts[key].risk_history == second.counts[key].risk_history


@pytest.mark.asyncio
async def test_assignments_doctor_a_and_b_isolated() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    doctor_b = await users.get_by_email("enrich-doctor-b@example.com")
    assert doctor_b is not None

    for patient_key, doctor in (
        ("a1", doctor_a),
        ("a2", doctor_a),
        ("a3", doctor_a),
        ("b1", doctor_b),
        ("b2", doctor_b),
    ):
        assignment = await assignments.get_by_patient_and_assignee(
            result.patient_ids[patient_key],
            doctor.id,
        )
        assert assignment is not None
        assert assignment.status.value == "active"

    cross = await assignments.get_by_patient_and_assignee(result.patient_ids["a1"], doctor_b.id)
    assert cross is None


@pytest.mark.asyncio
async def test_doctor_a_cannot_access_doctor_b_patient_via_service() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    patient_service = build_policy_patient_service(patients, memberships, assignments)
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await patient_service.get_patient_for_user_with_context(
            doctor_a.id,
            UserRole.DOCTOR,
            result.patient_ids["b1"],
        )


@pytest.mark.asyncio
async def test_clinic_admin_lists_enrichment_patients() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    patient_service = build_policy_patient_service(patients, memberships, assignments)
    listed = await patient_service.list_patients_for_user(
        admin.id,
        UserRole.CLINIC_ADMIN,
        page=1,
        page_size=50,
    )
    enrich_ids = {
        p.id for p in listed.items if p.notes and any(m in p.notes for m in ENRICHMENT_MARKERS)
    }
    assert len(enrich_ids) == 5


@pytest.mark.asyncio
async def test_timeline_and_pdf_sources_non_empty_for_a1() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    patient_id = result.patient_ids["a1"]

    timeline_service = build_clinical_timeline_service(
        patients,
        measurements,
        records,
        appointments,
        memberships,
        assignments,
    )
    timeline, _ = await timeline_service.get_clinical_timeline(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient_id,
    )
    assert len(timeline.events) >= 2

    pdf_service = build_patient_health_report_service(
        patients,
        records,
        measurements,
        memberships,
        assignments,
    )
    pdf_bytes, _filename, _org = await pdf_service.generate_pdf(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=patient_id,
        locale="en",
    )
    assert len(pdf_bytes) > 500


@pytest.mark.asyncio
async def test_pdf_datasource_non_empty_for_all_enrichment_patients() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    doctor_b = await users.get_by_email("enrich-doctor-b@example.com")
    assert doctor_b is not None
    pdf_service = build_patient_health_report_service(
        patients,
        records,
        measurements,
        memberships,
        assignments,
    )
    actors = {"a1": doctor_a, "a2": doctor_a, "b1": doctor_b, "b2": doctor_b}
    for key, actor in actors.items():
        pdf_bytes, _, _ = await pdf_service.generate_pdf(
            actor.id,
            UserRole.DOCTOR,
            patient_id=result.patient_ids[key],
            locale="en",
        )
        assert len(pdf_bytes) > 500


@pytest.mark.asyncio
async def test_analyze_doctor_b_missing_does_not_alias_doctor_a() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await analyze_demo_clinical_enrichment(**kwargs)
    assert result.mutate is False
    assert result.doctor_b_user_id is None
    assert result.doctor_b_status == "doctor_b_missing"
    assert result.doctor_a_user_id == doctor_a.id
    assert result.doctor_b_user_id != result.doctor_a_user_id
    assert result.patient_ids == {}


@pytest.mark.asyncio
async def test_mutate_fails_when_doctor_b_password_missing() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    kwargs["config"] = DemoClinicalEnrichmentConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password=None,
    )
    with pytest.raises(ValueError, match="DEMO_DOCTOR_B_PASSWORD"):
        await seed_demo_clinical_enrichment(**kwargs, mutate=True)


@pytest.mark.asyncio
async def test_analyze_fails_when_doctor_b_email_matches_doctor_a() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email=doctor_a.email,
        doctor_b_password="DoctorBPass12345!",
    )
    with pytest.raises(ValueError, match="DEMO_DOCTOR_B_EMAIL must differ"):
        await analyze_demo_clinical_enrichment(**kwargs)


@pytest.mark.asyncio
async def test_mutate_fails_when_doctor_b_still_missing_after_ensure() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    kwargs["config"] = DemoClinicalEnrichmentConfig(
        organization_slug=DEMO_ORGANIZATION_SLUG,
        clinic_admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="",
    )
    with pytest.raises(ValueError, match="DEMO_DOCTOR_B_PASSWORD"):
        await seed_demo_clinical_enrichment(**kwargs, mutate=True)


@pytest.mark.asyncio
async def test_risk_types_match_scenarios() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    expected = {
        "a1": RiskAssessmentType.DIABETES,
        "a2": RiskAssessmentType.HEART_DISEASE,
        "b1": RiskAssessmentType.HEART_DISEASE,
        "b2": RiskAssessmentType.STROKE,
    }
    for key, assessment_type in expected.items():
        rows = await risk.list_by_patient(result.patient_ids[key], limit=10)
        assert any(row.assessment_type == assessment_type for row in rows)


@pytest.mark.asyncio
async def test_enrichment_v2_expected_clinical_counts() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    expected = {
        "a1": {"measurements": 7, "medical_records": 4},
        "a2": {"measurements": 5, "medical_records": 5},
        "b1": {"measurements": 3, "medical_records": 2},
        "b2": {"measurements": 4, "medical_records": 5},
    }
    for key, counts in expected.items():
        assert result.counts[key].measurements == counts["measurements"]
        assert result.counts[key].medical_records == counts["medical_records"]


@pytest.mark.asyncio
async def test_enrichment_v2_medical_records_include_lab_imaging_and_medications() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    for key in ("a1", "a2", "b1", "b2"):
        pid = result.patient_ids[key]
        rows = await records.list_by_owner(admin.id, patient_id=pid, limit=50)
        assert any(row.record_type == "lab_result" for row in rows)
        assert any((row.diagnosis or "").strip() for row in rows)
    assert any(
        row.medications
        for row in await records.list_by_owner(
            admin.id,
            patient_id=result.patient_ids["a1"],
            limit=50,
        )
    )
    assert any(
        row.record_type == "imaging"
        for row in await records.list_by_owner(
            admin.id,
            patient_id=result.patient_ids["a2"],
            limit=50,
        )
    )


@pytest.mark.asyncio
async def test_timeline_event_types_diverse_for_a2() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    timeline_service = build_clinical_timeline_service(
        patients,
        measurements,
        records,
        appointments,
        memberships,
        assignments,
    )
    timeline, _ = await timeline_service.get_clinical_timeline(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=result.patient_ids["a2"],
    )
    event_types = {event.event_type for event in timeline.events}
    assert "health_measurement" in event_types
    assert "medical_record_diagnosis" in event_types
    assert "medical_record_medication" in event_types
    assert "medical_record_treatment" in event_types
    assert "appointment_completed" in event_types or "appointment_scheduled" in event_types
    detail_blob = " ".join(event.detail for event in timeline.events)
    assert "seed:demo-enrich" not in detail_blob


@pytest.mark.asyncio
async def test_a2_canonical_risk_history_has_score_and_level_for_ui() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    result = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    rows = await risk.list_by_patient(result.patient_ids["a2"])
    assert len(rows) == 1
    row = rows[0]
    assert row.assessment_type == RiskAssessmentType.HEART_DISEASE
    assert row.risk_level == "moderate"
    assert row.score == 58.0
    assert row.result_snapshot is not None
    factors = row.result_snapshot.get("contributing_factors")
    assert factors
    assert len(factors) == 3
    tr_messages = [f.get("message_tr", "") for f in factors]
    assert any("Kan basıncı" in msg for msg in tr_messages)
    assert any("takip ölçümleri" in msg for msg in tr_messages)
    assert any("kardiyak takip" in msg for msg in tr_messages)


@pytest.mark.asyncio
async def test_a3_stroke_demo_idempotent_and_doctor_b_isolated() -> None:
    users, orgs, memberships, assignments, patients, consents, measurements, records, appointments, risk = (
        await _base_repos()
    )
    org, admin, doctor_a = await _seed_org_admin_doctor_a(users, orgs, memberships)
    kwargs = _enrichment_kwargs(
        users,
        orgs,
        memberships,
        patients,
        assignments,
        consents,
        measurements,
        records,
        appointments,
        risk,
        admin_email=admin.email,
        doctor_a_email=doctor_a.email,
        doctor_b_email="enrich-doctor-b@example.com",
        doctor_b_password="DoctorBPass12345!",
    )
    first = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    second = await seed_demo_clinical_enrichment(**kwargs, mutate=True)
    a3_id = first.patient_ids["a3"]
    assert first.counts["a3"].risk_history == 1
    assert first.counts["a3"].measurements >= 4
    assert second.counts["a3"].risk_history == first.counts["a3"].risk_history

    stroke_rows = await risk.list_by_patient(a3_id)
    assert len(stroke_rows) == 1
    assert stroke_rows[0].assessment_type == RiskAssessmentType.STROKE

    doctor_b = await users.get_by_email("enrich-doctor-b@example.com")
    assert doctor_b is not None
    assert await assignments.get_by_patient_and_assignee(a3_id, doctor_b.id) is None

    from app.core.exceptions import NotFoundError

    patient_service = build_policy_patient_service(patients, memberships, assignments)
    with pytest.raises(NotFoundError):
        await patient_service.get_patient_for_user_with_context(
            doctor_b.id,
            UserRole.DOCTOR,
            a3_id,
        )

    timeline_service = build_clinical_timeline_service(
        patients,
        measurements,
        records,
        appointments,
        memberships,
        assignments,
    )
    timeline, _ = await timeline_service.get_clinical_timeline(
        doctor_a.id,
        UserRole.DOCTOR,
        patient_id=a3_id,
    )
    assert timeline.events
    assert any(e.event_type == "medical_record_imaging_report" for e in timeline.events)
