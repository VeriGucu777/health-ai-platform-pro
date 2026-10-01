"""Idempotent demo clinical enrichment for live walkthrough (ops seed only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.seeding.demo_clinic_admin_seed import (
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_NAME,
    DEMO_ORGANIZATION_SLUG,
)
from app.application.seeding.demo_doctor_b_user_seed import (
    DEFAULT_DEMO_DOCTOR_B_EMAIL,
    DemoDoctorBUserSeedConfig,
    ensure_demo_doctor_b_user,
)
from app.application.seeding.demo_doctor_user_seed import (
    DEMO_DOCTOR_EMAIL,
    DemoDoctorUserSeedConfig,
    ensure_demo_doctor_user,
)
from app.application.seeding.demo_organization_fixture_seed import _find_demo_patient_in_org
from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType
from app.domain.entities.appointment import Appointment
from app.domain.entities.health_measurement import HealthMeasurement
from app.domain.entities.medical_record import MedicalRecord
from app.domain.entities.patient import Patient
from app.domain.entities.user import UserRole
from app.domain.entities.risk_assessment_history import RiskAssessmentHistory
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository
from app.domain.interfaces.user_repository import UserRepository
from app.domain.organization.entities import OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.domain.risk.enums import RULE_BASED_MODEL_KIND, RiskAssessmentType
from app.infrastructure.repositories.user_repository import normalize_email

MARKER_A1 = "seed:demo-enrich-a1"
MARKER_A2 = "seed:demo-enrich-a2"
MARKER_B1 = "seed:demo-enrich-b1"
MARKER_B2 = "seed:demo-enrich-b2"

ENRICHMENT_MARKERS = (MARKER_A1, MARKER_A2, MARKER_B1, MARKER_B2)

# Bump when measurement/record templates change. Older rows use /meas/00 and /record/00
# (pre-v2); re-seed adds v2 rows idempotently. Production may need soft-deactivate of
# legacy repetitive measurements (notes matching .../meas/0[0-4] without /v2/).
ENRICHMENT_CLINICAL_DATA_VERSION = "v2"

class OrganizationSeedRepository(Protocol):
    async def get_by_slug(self, slug: str): ...


@dataclass(frozen=True)
class EnrichmentPatientSpec:
    key: str
    marker: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    doctor_slot: str  # "a" | "b"
    primary_risk: RiskAssessmentType


@dataclass(frozen=True)
class DemoClinicalEnrichmentConfig:
    organization_slug: str = DEMO_ORGANIZATION_SLUG
    organization_name: str = DEMO_ORGANIZATION_NAME
    clinic_admin_email: str = DEMO_CLINIC_ADMIN_EMAIL
    doctor_a_email: str = DEMO_DOCTOR_EMAIL
    doctor_b_email: str = DEFAULT_DEMO_DOCTOR_B_EMAIL
    doctor_b_password: str | None = None
    doctor_b_display_name: str = "Demo Doctor Two"
    doctor_a_password: str | None = None


@dataclass
class PatientEnrichmentCounts:
    measurements: int = 0
    medical_records: int = 0
    appointments: int = 0
    risk_history: int = 0
    consent_granted: bool = False
    assignment_active: bool = False


@dataclass
class DemoClinicalEnrichmentSeedResult:
    organization_id: UUID
    doctor_a_user_id: UUID
    doctor_b_user_id: UUID | None
    patient_ids: dict[str, UUID]
    created_patients: dict[str, bool] = field(default_factory=dict)
    counts: dict[str, PatientEnrichmentCounts] = field(default_factory=dict)
    mutate: bool = False
    doctor_b_status: str = "doctor_b_missing"


PATIENT_SPECS: tuple[EnrichmentPatientSpec, ...] = (
    EnrichmentPatientSpec(
        key="a1",
        marker=MARKER_A1,
        first_name="Demo",
        last_name="Diabetes Follow-up Patient",
        date_of_birth=date(1972, 4, 18),
        gender="female",
        doctor_slot="a",
        primary_risk=RiskAssessmentType.DIABETES,
    ),
    EnrichmentPatientSpec(
        key="a2",
        marker=MARKER_A2,
        first_name="Demo",
        last_name="Cardiac Follow-up Patient",
        date_of_birth=date(1966, 9, 3),
        gender="male",
        doctor_slot="a",
        primary_risk=RiskAssessmentType.HEART_DISEASE,
    ),
    EnrichmentPatientSpec(
        key="b1",
        marker=MARKER_B1,
        first_name="Demo",
        last_name="Preventive Follow-up Patient",
        date_of_birth=date(1990, 11, 22),
        gender="female",
        doctor_slot="b",
        primary_risk=RiskAssessmentType.HEART_DISEASE,
    ),
    EnrichmentPatientSpec(
        key="b2",
        marker=MARKER_B2,
        first_name="Demo",
        last_name="Stroke Follow-up Patient",
        date_of_birth=date(1958, 7, 7),
        gender="male",
        doctor_slot="b",
        primary_risk=RiskAssessmentType.STROKE,
    ),
)


def _notes_has_marker(notes: str | None, sub_marker: str) -> bool:
    return sub_marker in (notes or "")


def _enrichment_sub_marker(spec: EnrichmentPatientSpec, kind: str, index: int) -> str:
    return f"{spec.marker}/{kind}/{ENRICHMENT_CLINICAL_DATA_VERSION}/{index:02d}"


def _validate_doctor_b_email_distinct_from_a(config: DemoClinicalEnrichmentConfig) -> None:
    if normalize_email(config.doctor_b_email) == normalize_email(config.doctor_a_email):
        msg = (
            "DEMO_DOCTOR_B_EMAIL must differ from demo doctor A email; "
            "doctor_a_user_id and doctor_b_user_id must not resolve to the same user."
        )
        raise ValueError(msg)


def _assert_doctor_ids_distinct(*, doctor_a_id: UUID, doctor_b_id: UUID | None, mutate: bool) -> None:
    if doctor_b_id is None:
        if mutate:
            msg = (
                "Demo doctor B is missing; run analyze first or set DEMO_DOCTOR_B_EMAIL. "
                "Use --confirm-seed with DEMO_DOCTOR_B_PASSWORD to create doctor B."
            )
            raise ValueError(msg)
        return
    if doctor_a_id == doctor_b_id:
        msg = "doctor_a_user_id must not equal doctor_b_user_id; check DEMO_DOCTOR_B_EMAIL configuration."
        raise ValueError(msg)


def _require_doctor_b_password_for_mutate(config: DemoClinicalEnrichmentConfig, *, mutate: bool) -> None:
    if not mutate:
        return
    if not config.doctor_b_password or not config.doctor_b_password.strip():
        msg = "DEMO_DOCTOR_B_PASSWORD is required with --confirm-seed."
        raise ValueError(msg)


def _snapshot_has_marker(snapshot: dict[str, Any] | None, sub_marker: str) -> bool:
    if not snapshot:
        return False
    return snapshot.get("seed_marker") == sub_marker


async def _validate_organization(organization_repository: OrganizationSeedRepository, slug: str):
    organization = await organization_repository.get_by_slug(slug)
    if organization is None:
        msg = f"Organization slug {slug!r} not found."
        raise ValueError(msg)
    if organization.slug != DEMO_ORGANIZATION_SLUG:
        msg = f"Refusing enrichment: expected slug {DEMO_ORGANIZATION_SLUG!r}, got {organization.slug!r}"
        raise ValueError(msg)
    return organization


async def _ensure_doctor_membership(
    *,
    membership_repository: OrganizationMembershipRepository,
    organization_id: UUID,
    user_id: UUID,
    mutate: bool,
) -> bool:
    membership = await membership_repository.get_by_organization_and_user(organization_id, user_id)
    if membership is None:
        if not mutate:
            return False
        await membership_repository.create(
            OrganizationMembership(
                organization_id=organization_id,
                user_id=user_id,
                membership_role=OrganizationMembershipRole.DOCTOR,
                status=MembershipStatus.ACTIVE,
            ),
        )
        return True
    if membership.status != MembershipStatus.ACTIVE:
        if not mutate:
            return False
        membership.status = MembershipStatus.ACTIVE
        membership.membership_role = OrganizationMembershipRole.DOCTOR
        await membership_repository.update(membership)
        return True
    return False


async def _ensure_patient(
    *,
    patient_repository: PatientRepository,
    organization_id: UUID,
    owner_id: UUID,
    spec: EnrichmentPatientSpec,
    mutate: bool,
) -> tuple[Patient | None, bool]:
    org_patients = await patient_repository.list_by_organization_ids(
        [organization_id],
        offset=0,
        limit=500,
    )
    existing = _find_demo_patient_in_org(
        org_patients,
        marker=spec.marker,
        first_name=spec.first_name,
        last_name=spec.last_name,
        date_of_birth=spec.date_of_birth,
    )
    if existing is not None:
        updated = False
        if mutate and (existing.notes or "") != spec.marker:
            existing.notes = spec.marker
            existing.is_active = True
            existing.touch()
            existing = await patient_repository.update(existing)
            updated = True
        return existing, updated

    if not mutate:
        return None, False

    patient = await patient_repository.create(
        Patient(
            owner_id=owner_id,
            organization_id=organization_id,
            first_name=spec.first_name,
            last_name=spec.last_name,
            date_of_birth=spec.date_of_birth,
            gender=spec.gender,
            notes=spec.marker,
            is_active=True,
        ),
    )
    return patient, True


async def _ensure_assignment(
    *,
    assignment_repository: PatientAssignmentRepository,
    organization_id: UUID,
    patient_id: UUID,
    doctor_id: UUID,
    assigned_by: UUID,
    mutate: bool,
) -> bool:
    assignment = await assignment_repository.get_by_patient_and_assignee(patient_id, doctor_id)
    if assignment is None:
        if not mutate:
            return False
        await assignment_repository.create(
            PatientAssignment(
                organization_id=organization_id,
                patient_id=patient_id,
                assignee_user_id=doctor_id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
                assigned_by_user_id=assigned_by,
            ),
        )
        return True
    if assignment.status != AssignmentStatus.ACTIVE:
        if not mutate:
            return False
        assignment.status = AssignmentStatus.ACTIVE
        assignment.is_primary = True
        assignment.organization_id = organization_id
        assignment.assigned_by_user_id = assigned_by
        await assignment_repository.update(assignment)
        return True
    return False


async def _ensure_consent(
    *,
    consent_repository: PatientConsentRepository,
    patient_id: UUID,
    organization_id: UUID,
    recorded_by: UUID,
    mutate: bool,
) -> bool:
    active = await consent_repository.get_active_granted(
        patient_id,
        organization_id,
        ConsentType.CLINICAL_DATA_PROCESSING,
    )
    if active is not None:
        return False
    if not mutate:
        return False
    version = await consent_repository.get_max_version(
        patient_id,
        organization_id,
        ConsentType.CLINICAL_DATA_PROCESSING,
    )
    now = datetime.now(UTC)
    await consent_repository.create(
        PatientConsent(
            patient_id=patient_id,
            organization_id=organization_id,
            consent_type=ConsentType.CLINICAL_DATA_PROCESSING,
            status=ConsentStatus.GRANTED,
            granted_at=now,
            recorded_by_user_id=recorded_by,
            version=version + 1,
            source=ConsentSource.MANUAL,
        ),
    )
    return True


async def _count_measurements(
    measurement_repository: HealthMeasurementRepository,
    owner_id: UUID,
    patient_id: UUID,
) -> int:
    rows = await measurement_repository.list_by_owner(
        owner_id,
        patient_id=patient_id,
        limit=500,
    )
    return len(rows)


async def _seed_measurements_for_spec(
    *,
    measurement_repository: HealthMeasurementRepository,
    owner_id: UUID,
    patient: Patient,
    spec: EnrichmentPatientSpec,
    mutate: bool,
) -> int:
    templates = _measurement_templates(spec)
    created = 0
    existing = await measurement_repository.list_by_owner(owner_id, patient_id=patient.id, limit=500)
    for idx, template in enumerate(templates):
        sub_marker = _enrichment_sub_marker(spec, "meas", idx)
        if any(_notes_has_marker(row.notes, sub_marker) for row in existing):
            continue
        if not mutate:
            continue
        await measurement_repository.create(
            HealthMeasurement(
                owner_id=owner_id,
                patient_id=patient.id,
                measured_at=template["measured_at"],
                blood_glucose=template.get("blood_glucose"),
                glucose_context=template.get("glucose_context"),
                systolic_pressure=template.get("systolic_pressure"),
                diastolic_pressure=template.get("diastolic_pressure"),
                heart_rate=template.get("heart_rate"),
                weight_kg=template.get("weight_kg"),
                exercise_minutes=template.get("exercise_minutes"),
                notes=sub_marker,
            ),
        )
        created += 1
    return created


def _measurement_templates(spec: EnrichmentPatientSpec) -> list[dict[str, Any]]:
    base = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    if spec.key == "a1":
        return [
            {
                "measured_at": base - timedelta(days=88),
                "blood_glucose": Decimal("118"),
                "glucose_context": "fasting",
            },
            {
                "measured_at": base - timedelta(days=62),
                "blood_glucose": Decimal("126"),
                "glucose_context": "post_meal",
                "meal_context": "after lunch",
            },
            {
                "measured_at": base - timedelta(days=45),
                "blood_glucose": Decimal("112"),
                "glucose_context": "fasting",
                "weight_kg": Decimal("77.8"),
            },
            {
                "measured_at": base - timedelta(days=28),
                "blood_glucose": Decimal("121"),
                "glucose_context": "post_meal",
            },
            {
                "measured_at": base - timedelta(days=21),
                "systolic_pressure": 128,
                "diastolic_pressure": 82,
            },
            {
                "measured_at": base - timedelta(days=12),
                "systolic_pressure": 124,
                "diastolic_pressure": 80,
                "blood_glucose": Decimal("109"),
                "glucose_context": "fasting",
            },
            {
                "measured_at": base - timedelta(days=4),
                "systolic_pressure": 122,
                "diastolic_pressure": 78,
                "exercise_minutes": 30,
            },
        ]
    if spec.key == "a2":
        return [
            {
                "measured_at": base - timedelta(days=68),
                "systolic_pressure": 138,
                "diastolic_pressure": 88,
                "weight_kg": Decimal("91.5"),
            },
            {
                "measured_at": base - timedelta(days=42),
                "blood_glucose": Decimal("104"),
                "glucose_context": "fasting",
            },
            {
                "measured_at": base - timedelta(days=26),
                "systolic_pressure": 130,
                "diastolic_pressure": 84,
            },
            {
                "measured_at": base - timedelta(days=14),
                "blood_glucose": Decimal("118"),
                "glucose_context": "post_meal",
            },
            {
                "measured_at": base - timedelta(days=3),
                "systolic_pressure": 126,
                "diastolic_pressure": 80,
                "heart_rate": 68,
            },
        ]
    if spec.key == "b1":
        return [
            {
                "measured_at": base - timedelta(days=35),
                "systolic_pressure": 118,
                "diastolic_pressure": 76,
            },
            {
                "measured_at": base - timedelta(days=18),
                "blood_glucose": Decimal("92"),
                "glucose_context": "fasting",
                "exercise_minutes": 40,
            },
            {
                "measured_at": base - timedelta(days=6),
                "systolic_pressure": 114,
                "diastolic_pressure": 72,
            },
        ]
    return [
        {
            "measured_at": base - timedelta(days=72),
            "systolic_pressure": 142,
            "diastolic_pressure": 86,
        },
        {
            "measured_at": base - timedelta(days=48),
            "systolic_pressure": 134,
            "diastolic_pressure": 84,
            "weight_kg": Decimal("83.2"),
        },
        {
            "measured_at": base - timedelta(days=22),
            "systolic_pressure": 128,
            "diastolic_pressure": 80,
        },
        {
            "measured_at": base - timedelta(days=5),
            "blood_glucose": Decimal("101"),
            "glucose_context": "fasting",
        },
    ]


async def _seed_medical_records(
    *,
    medical_record_repository: MedicalRecordRepository,
    owner_id: UUID,
    patient: Patient,
    spec: EnrichmentPatientSpec,
    mutate: bool,
) -> int:
    specs = _medical_record_specs(spec)
    created = 0
    existing = await medical_record_repository.list_by_owner(owner_id, patient_id=patient.id, limit=100)
    for idx, row in enumerate(specs):
        sub_marker = _enrichment_sub_marker(spec, "record", idx)
        if any(_notes_has_marker(rec.notes, sub_marker) for rec in existing):
            continue
        if not mutate:
            continue
        await medical_record_repository.create(
            MedicalRecord(
                owner_id=owner_id,
                patient_id=patient.id,
                record_date=row["record_date"],
                record_type=row["record_type"],
                title=row["title"],
                description=row.get("description"),
                diagnosis=row.get("diagnosis"),
                treatment=row.get("treatment"),
                medications=row.get("medications"),
                doctor_name=row.get("doctor_name"),
                hospital_name=row.get("hospital_name"),
                notes=sub_marker,
            ),
        )
        created += 1
    return created


def _medical_record_specs(spec: EnrichmentPatientSpec) -> list[dict[str, Any]]:
    base = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)
    if spec.key == "a1":
        return [
            {
                "record_date": base - timedelta(days=110),
                "record_type": "visit",
                "title": "Endocrine follow-up (demo)",
                "diagnosis": "Type 2 diabetes mellitus (synthetic demo history for decision-support review).",
            },
            {
                "record_date": base - timedelta(days=55),
                "record_type": "lab_result",
                "title": "Metabolic laboratory panel (demo)",
                "diagnosis": (
                    "Synthetic laboratory summary (demo): HbA1c 7.2%; LDL 142 mg/dL; "
                    "triglycerides 180 mg/dL."
                ),
                "description": "Fictional demo values for decision-support review only.",
            },
            {
                "record_date": base - timedelta(days=40),
                "record_type": "visit",
                "title": "Medication review (demo)",
                "medications": (
                    "Metformin dose increased per clinic protocol (synthetic demo note; "
                    "not a prescribing instruction)."
                ),
            },
            {
                "record_date": base - timedelta(days=15),
                "record_type": "visit",
                "title": "Diabetes follow-up plan (demo)",
                "treatment": (
                    "Continue home glucose logging, quarterly HbA1c, and lifestyle counseling "
                    "(synthetic care plan for demo)."
                ),
            },
        ]
    if spec.key == "a2":
        return [
            {
                "record_date": base - timedelta(days=95),
                "record_type": "visit",
                "title": "Cardiovascular clinic visit (demo)",
                "diagnosis": (
                    "Hypertension with elevated cardiovascular risk profile "
                    "(synthetic demo history)."
                ),
            },
            {
                "record_date": base - timedelta(days=70),
                "record_type": "lab_result",
                "title": "Lipid panel (demo)",
                "diagnosis": (
                    "Synthetic lipid panel (demo): LDL 156 mg/dL; HDL 42 mg/dL; "
                    "triglycerides 190 mg/dL."
                ),
                "description": "Fictional demo values for decision-support review only.",
            },
            {
                "record_date": base - timedelta(days=50),
                "record_type": "visit",
                "title": "Medication adjustment (demo)",
                "medications": (
                    "Antihypertensive and statin therapy reviewed; dose adjustment noted "
                    "(synthetic demo text only)."
                ),
            },
            {
                "record_date": base - timedelta(days=32),
                "record_type": "imaging",
                "title": "Echocardiography summary (demo)",
                "diagnosis": (
                    "Synthetic echocardiography report summary (demo): documented for chart "
                    "review; no image file or automated analysis."
                ),
                "description": "Fictional demo imaging narrative for decision-support review only.",
            },
            {
                "record_date": base - timedelta(days=14),
                "record_type": "visit",
                "title": "Cardiac follow-up plan (demo)",
                "treatment": (
                    "Blood pressure targets, lipid recheck in 3 months, and activity guidance "
                    "(synthetic demo plan)."
                ),
            },
        ]
    if spec.key == "b1":
        return [
            {
                "record_date": base - timedelta(days=55),
                "record_type": "visit",
                "title": "Preventive screening visit (demo)",
                "diagnosis": (
                    "Preventive screening visit; no major abnormality documented in this "
                    "synthetic demo record."
                ),
            },
            {
                "record_date": base - timedelta(days=25),
                "record_type": "lab_result",
                "title": "Preventive screening panel (demo)",
                "diagnosis": (
                    "Synthetic preventive screening summary (demo): fasting glucose 92 mg/dL; "
                    "no major abnormality in fictional demo panel."
                ),
            },
        ]
    return [
        {
            "record_date": base - timedelta(days=85),
            "record_type": "visit",
            "title": "Cerebrovascular follow-up (demo)",
            "diagnosis": (
                "History of cerebrovascular event under outpatient follow-up "
                "(synthetic demo history)."
            ),
        },
        {
            "record_date": base - timedelta(days=60),
            "record_type": "lab_result",
            "title": "Stroke follow-up laboratories (demo)",
            "diagnosis": (
                "Synthetic laboratory summary (demo): LDL 138 mg/dL; fasting glucose 101 mg/dL."
            ),
        },
        {
            "record_date": base - timedelta(days=45),
            "record_type": "visit",
            "title": "Secondary prevention medications (demo)",
            "medications": (
                "Antiplatelet and statin therapy continuation reviewed "
                "(synthetic demo medication note)."
            ),
        },
        {
            "record_date": base - timedelta(days=28),
            "record_type": "imaging",
            "title": "Brain imaging report summary (demo)",
            "diagnosis": (
                "Synthetic brain imaging report summary (demo); no DICOM file or "
                "automated image interpretation."
            ),
        },
        {
            "record_date": base - timedelta(days=10),
            "record_type": "visit",
            "title": "Stroke recovery follow-up plan (demo)",
            "treatment": (
                "Neurology follow-up, blood pressure monitoring, and rehabilitation goals "
                "(synthetic demo care plan)."
            ),
        },
    ]


async def _seed_appointments(
    *,
    appointment_repository: AppointmentRepository,
    owner_id: UUID,
    patient: Patient,
    spec: EnrichmentPatientSpec,
    mutate: bool,
) -> int:
    appts = _appointment_specs(spec)
    created = 0
    existing = await appointment_repository.list_by_owner(owner_id, patient_id=patient.id, limit=100)
    for idx, row in enumerate(appts):
        sub_marker = f"{spec.marker}/appt/{idx:02d}"
        if any(_notes_has_marker(ap.notes, sub_marker) for ap in existing):
            continue
        if not mutate:
            continue
        await appointment_repository.create(
            Appointment(
                owner_id=owner_id,
                patient_id=patient.id,
                appointment_date=row["appointment_date"],
                appointment_type=row["appointment_type"],
                status=row["status"],
                notes=sub_marker,
            ),
        )
        created += 1
    return created


def _appointment_specs(spec: EnrichmentPatientSpec) -> list[dict[str, Any]]:
    future = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
    past = datetime(2026, 4, 5, 11, 0, tzinfo=UTC)
    if spec.key == "b1":
        return [
            {"appointment_date": past, "appointment_type": "preventive", "status": "completed"},
        ]
    return [
        {"appointment_date": past, "appointment_type": "follow_up", "status": "completed"},
        {"appointment_date": future, "appointment_type": "follow_up", "status": "scheduled"},
    ]


async def _seed_risk_history(
    *,
    risk_repository: RiskAssessmentHistoryRepository,
    patient: Patient,
    organization_id: UUID,
    evaluator_id: UUID,
    spec: EnrichmentPatientSpec,
    mutate: bool,
) -> int:
    sub_marker = f"{spec.marker}/risk/primary"
    existing = await risk_repository.list_by_patient(patient.id, limit=50)
    if any(_snapshot_has_marker(row.result_snapshot, sub_marker) for row in existing):
        return 0
    if not mutate:
        return 0
    evaluated_at = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
    probability = {"a1": 0.38, "a2": 0.41, "b1": 0.18, "b2": 0.44}[spec.key]
    risk_level = "moderate" if spec.key != "b1" else "low"
    await risk_repository.append(
        RiskAssessmentHistory(
            patient_id=patient.id,
            organization_id=organization_id,
            assessment_type=spec.primary_risk,
            assessment_status="complete",
            risk_level=risk_level,
            score=52.0 if spec.key != "b1" else 28.0,
            probability=probability,
            model_kind=RULE_BASED_MODEL_KIND,
            model_version="rule_based_v1",
            evaluated_by_user_id=evaluator_id,
            evaluated_at=evaluated_at,
            result_snapshot={"seed_marker": sub_marker, "demo": True},
        ),
    )
    return 1


async def analyze_demo_clinical_enrichment(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: OrganizationMembershipRepository,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
    consent_repository: PatientConsentRepository,
    measurement_repository: HealthMeasurementRepository,
    medical_record_repository: MedicalRecordRepository,
    appointment_repository: AppointmentRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    config: DemoClinicalEnrichmentConfig | None = None,
) -> DemoClinicalEnrichmentSeedResult:
    """Dry-run analysis — validates org and reports expected enrichment state."""
    return await seed_demo_clinical_enrichment(
        user_repository=user_repository,
        organization_repository=organization_repository,
        membership_repository=membership_repository,
        patient_repository=patient_repository,
        assignment_repository=assignment_repository,
        consent_repository=consent_repository,
        measurement_repository=measurement_repository,
        medical_record_repository=medical_record_repository,
        appointment_repository=appointment_repository,
        risk_history_repository=risk_history_repository,
        config=config,
        mutate=False,
    )


async def seed_demo_clinical_enrichment(
    *,
    user_repository: UserRepository,
    organization_repository: OrganizationSeedRepository,
    membership_repository: OrganizationMembershipRepository,
    patient_repository: PatientRepository,
    assignment_repository: PatientAssignmentRepository,
    consent_repository: PatientConsentRepository,
    measurement_repository: HealthMeasurementRepository,
    medical_record_repository: MedicalRecordRepository,
    appointment_repository: AppointmentRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    config: DemoClinicalEnrichmentConfig | None = None,
    mutate: bool = False,
) -> DemoClinicalEnrichmentSeedResult:
    """Ensure demo doctors, patients, assignments, consent, and clinical demo data."""
    cfg = config or DemoClinicalEnrichmentConfig()
    _validate_doctor_b_email_distinct_from_a(cfg)
    _require_doctor_b_password_for_mutate(cfg, mutate=mutate)
    organization = await _validate_organization(organization_repository, cfg.organization_slug)

    clinic_admin = await user_repository.get_by_email(normalize_email(cfg.clinic_admin_email))
    if clinic_admin is None or clinic_admin.role != UserRole.CLINIC_ADMIN:
        msg = f"Clinic admin {cfg.clinic_admin_email!r} not found or wrong role."
        raise ValueError(msg)

    if mutate and cfg.doctor_a_password:
        await ensure_demo_doctor_user(
            user_repository,
            config=DemoDoctorUserSeedConfig(
                email=cfg.doctor_a_email,
                password=cfg.doctor_a_password,
            ),
        )
    doctor_a = await user_repository.get_by_email(normalize_email(cfg.doctor_a_email))
    if doctor_a is None or doctor_a.role != UserRole.DOCTOR:
        msg = f"Demo doctor A {cfg.doctor_a_email!r} not found."
        raise ValueError(msg)

    if mutate:
        await ensure_demo_doctor_b_user(
            user_repository,
            config=DemoDoctorBUserSeedConfig(
                email=cfg.doctor_b_email,
                password=cfg.doctor_b_password,
                display_name=cfg.doctor_b_display_name,
            ),
        )
    doctor_b = await user_repository.get_by_email(normalize_email(cfg.doctor_b_email))
    if doctor_b is None and mutate:
        msg = f"Demo doctor B {cfg.doctor_b_email!r} could not be ensured."
        raise ValueError(msg)

    _assert_doctor_ids_distinct(
        doctor_a_id=doctor_a.id,
        doctor_b_id=doctor_b.id if doctor_b is not None else None,
        mutate=mutate,
    )

    await _ensure_doctor_membership(
        membership_repository=membership_repository,
        organization_id=organization.id,
        user_id=doctor_a.id,
        mutate=mutate,
    )
    if doctor_b is not None:
        await _ensure_doctor_membership(
            membership_repository=membership_repository,
            organization_id=organization.id,
            user_id=doctor_b.id,
            mutate=mutate,
        )

    patient_ids: dict[str, UUID] = {}
    created_patients: dict[str, bool] = {}
    counts: dict[str, PatientEnrichmentCounts] = {}

    doctors = {"a": doctor_a, "b": doctor_b}

    for spec in PATIENT_SPECS:
        doctor = doctors.get(spec.doctor_slot)
        if doctor is None:
            if spec.doctor_slot == "b" and not mutate:
                continue
            msg = f"Doctor slot {spec.doctor_slot!r} unavailable for patient {spec.key}"
            raise ValueError(msg)

        patient, created = await _ensure_patient(
            patient_repository=patient_repository,
            organization_id=organization.id,
            owner_id=clinic_admin.id,
            spec=spec,
            mutate=mutate,
        )
        if patient is None:
            continue

        patient_ids[spec.key] = patient.id
        created_patients[spec.key] = created

        await _ensure_assignment(
            assignment_repository=assignment_repository,
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            assigned_by=clinic_admin.id,
            mutate=mutate,
        )
        await _ensure_consent(
            consent_repository=consent_repository,
            patient_id=patient.id,
            organization_id=organization.id,
            recorded_by=clinic_admin.id,
            mutate=mutate,
        )
        active_consent = await consent_repository.get_active_granted(
            patient.id,
            organization.id,
            ConsentType.CLINICAL_DATA_PROCESSING,
        )
        assignment_row = await assignment_repository.get_by_patient_and_assignee(
            patient.id,
            doctor.id,
        )
        assignment_active = (
            assignment_row is not None and assignment_row.status == AssignmentStatus.ACTIVE
        )

        if mutate:
            await _seed_measurements_for_spec(
                measurement_repository=measurement_repository,
                owner_id=clinic_admin.id,
                patient=patient,
                spec=spec,
                mutate=True,
            )
            await _seed_medical_records(
                medical_record_repository=medical_record_repository,
                owner_id=clinic_admin.id,
                patient=patient,
                spec=spec,
                mutate=True,
            )
            await _seed_appointments(
                appointment_repository=appointment_repository,
                owner_id=clinic_admin.id,
                patient=patient,
                spec=spec,
                mutate=True,
            )
            await _seed_risk_history(
                risk_repository=risk_history_repository,
                patient=patient,
                organization_id=organization.id,
                evaluator_id=doctor.id,
                spec=spec,
                mutate=True,
            )

        counts[spec.key] = PatientEnrichmentCounts(
            measurements=await _count_measurements(
                measurement_repository,
                clinic_admin.id,
                patient.id,
            ),
            medical_records=len(
                await medical_record_repository.list_by_owner(
                    clinic_admin.id,
                    patient_id=patient.id,
                    limit=100,
                ),
            ),
            appointments=len(
                await appointment_repository.list_by_owner(
                    clinic_admin.id,
                    patient_id=patient.id,
                    limit=100,
                ),
            ),
            risk_history=await risk_history_repository.count_by_patient(patient.id),
            consent_granted=active_consent is not None,
            assignment_active=assignment_active,
        )

    doctor_b_status = "doctor_b_ready" if doctor_b is not None else "doctor_b_missing"

    return DemoClinicalEnrichmentSeedResult(
        organization_id=organization.id,
        doctor_a_user_id=doctor_a.id,
        doctor_b_user_id=doctor_b.id if doctor_b is not None else None,
        patient_ids=patient_ids,
        created_patients=created_patients,
        counts=counts,
        mutate=mutate,
        doctor_b_status=doctor_b_status,
    )
