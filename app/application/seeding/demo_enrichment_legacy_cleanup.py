"""Marker-scoped legacy demo enrichment cleanup (ops only, analyze by default)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from app.application.seeding.demo_clinical_enrichment import (
    ENRICHMENT_MARKERS,
    PATIENT_SPECS,
)
from app.application.seeding.demo_clinic_admin_seed import DEMO_ORGANIZATION_SLUG
from app.application.seeding.demo_organization_fixture_seed import _find_demo_patient_in_org
from app.application.clinical_child_soft_delete import soft_deactivate_clinical_child
from app.domain.entities.patient import Patient
from app.domain.interfaces.appointment_repository import AppointmentRepository
from app.domain.interfaces.health_measurement_repository import HealthMeasurementRepository
from app.domain.interfaces.medical_record_repository import MedicalRecordRepository
from app.domain.interfaces.organization_repository import OrganizationRepository
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.risk_assessment_history_repository import RiskAssessmentHistoryRepository

# Historical ops-only notes prefix (pre soft-delete migration); used only for marker normalization.
LEGACY_DEACTIVATED_PREFIX = "legacy-deactivated:v1:"

EXPECTED_LEGACY_MEASUREMENT_TOTAL = 18
EXPECTED_LEGACY_MEDICAL_RECORD_TOTAL = 7

EXPECTED_PRODUCTION_PATIENT_IDS: dict[str, UUID] = {
    "a1": UUID("8027c2b1-3d4a-4777-b5d7-f42e22bba15a"),
    "a2": UUID("43382858-a46e-4d2e-a33d-4f86b3c140ed"),
    "b1": UUID("0c184feb-13f1-4b07-99c3-ed9a4f245b1b"),
    "b2": UUID("b3980b67-63c3-4135-8d3f-e5ef2758a9e4"),
}

EXPECTED_LEGACY_MEASUREMENTS_BY_KEY: dict[str, int] = {
    "a1": 5,
    "a2": 5,
    "b1": 3,
    "b2": 5,
}

EXPECTED_LEGACY_MEDICAL_RECORDS_BY_KEY: dict[str, int] = {
    "a1": 2,
    "a2": 2,
    "b1": 1,
    "b2": 2,
}

# Production note: a1 risk history must remain untouched (expected count 3 at inventory time).
A1_RISK_HISTORY_INVENTORY_NOTE = "a1 risk_history count=3 (read-only note; cleanup does not mutate risk)."

_LEGACY_MEAS_NOTES_RE = re.compile(
    r"^seed:demo-enrich-(?:a1|a2|b1|b2)/meas/\d{2}$",
)
_LEGACY_RECORD_NOTES_RE = re.compile(
    r"^seed:demo-enrich-(?:a1|a2|b1|b2)/record/\d{2}$",
)
_ENRICHMENT_MARKER_IN_NOTES_RE = re.compile(r"seed:demo-enrich-(?:a1|a2|b1|b2)")

NotesClass = Literal[
    "legacy_active",
    "legacy_deactivated",
    "v2",
    "non_task3",
    "unrelated",
]


def _normalize_marker_notes(notes: str | None) -> str:
    text = (notes or "").strip()
    if text.startswith(LEGACY_DEACTIVATED_PREFIX):
        return text[len(LEGACY_DEACTIVATED_PREFIX) :].strip()
    return text


def classify_measurement_notes(notes: str | None, *, is_active: bool = True) -> NotesClass:
    raw = _normalize_marker_notes(notes)
    if "/v2/" in raw and _ENRICHMENT_MARKER_IN_NOTES_RE.search(raw):
        return "v2"
    if _LEGACY_MEAS_NOTES_RE.match(raw):
        return "legacy_active" if is_active else "legacy_deactivated"
    if _ENRICHMENT_MARKER_IN_NOTES_RE.search(raw):
        return "non_task3"
    return "unrelated"


def classify_medical_record_notes(notes: str | None, *, is_active: bool = True) -> NotesClass:
    raw = _normalize_marker_notes(notes)
    if "/v2/" in raw and _ENRICHMENT_MARKER_IN_NOTES_RE.search(raw):
        return "v2"
    if _LEGACY_RECORD_NOTES_RE.match(raw):
        return "legacy_active" if is_active else "legacy_deactivated"
    if _ENRICHMENT_MARKER_IN_NOTES_RE.search(raw):
        return "non_task3"
    return "unrelated"


def patient_marker_matches(patient: Patient, marker: str) -> bool:
    return (patient.notes or "").strip() == marker


@dataclass(frozen=True)
class DemoEnrichmentLegacyCleanupConfig:
    organization_slug: str = DEMO_ORGANIZATION_SLUG
    verify_production_patient_ids: bool = True


@dataclass
class PatientLegacyInventory:
    patient_key: str
    patient_id: UUID
    marker_ok: bool
    legacy_measurements_active: int = 0
    legacy_measurements_deactivated: int = 0
    legacy_medical_records_active: int = 0
    legacy_medical_records_deactivated: int = 0
    v2_measurements: int = 0
    v2_medical_records: int = 0
    non_task3_measurements: int = 0
    non_task3_medical_records: int = 0
    appointments: int = 0
    risk_history: int = 0
    assignments: int = 0
    consents: int = 0
    patient_is_active: bool = True


@dataclass
class LegacyCleanupInventory:
    patient_rows: list[PatientLegacyInventory] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def legacy_measurements_active(self) -> int:
        return sum(row.legacy_measurements_active for row in self.patient_rows)

    @property
    def legacy_medical_records_active(self) -> int:
        return sum(row.legacy_medical_records_active for row in self.patient_rows)

    @property
    def v2_measurements(self) -> int:
        return sum(row.v2_measurements for row in self.patient_rows)

    @property
    def v2_medical_records(self) -> int:
        return sum(row.v2_medical_records for row in self.patient_rows)

    @property
    def non_task3_measurements(self) -> int:
        return sum(row.non_task3_measurements for row in self.patient_rows)

    @property
    def non_task3_medical_records(self) -> int:
        return sum(row.non_task3_medical_records for row in self.patient_rows)


@dataclass(frozen=True)
class GuardCheckResult:
    ok: bool
    abort_reasons: tuple[str, ...] = ()


def validate_pre_cleanup_guards(
    inventory: LegacyCleanupInventory,
    *,
    strict_production_ids: bool = True,
) -> GuardCheckResult:
    reasons: list[str] = []
    if len(inventory.patient_rows) != 4:
        reasons.append(f"expected 4 target patients, found {len(inventory.patient_rows)}")
    for row in inventory.patient_rows:
        if not row.marker_ok:
            reasons.append(f"patient {row.patient_key} marker mismatch")
        if strict_production_ids:
            expected_id = EXPECTED_PRODUCTION_PATIENT_IDS.get(row.patient_key)
            if expected_id is not None and row.patient_id != expected_id:
                reasons.append(
                    f"patient {row.patient_key} id {row.patient_id} != expected production id",
                )
            exp_meas = EXPECTED_LEGACY_MEASUREMENTS_BY_KEY.get(row.patient_key, 0)
            if row.legacy_measurements_active != exp_meas:
                reasons.append(
                    f"patient {row.patient_key} legacy measurements "
                    f"{row.legacy_measurements_active} != expected {exp_meas}",
                )
            exp_rec = EXPECTED_LEGACY_MEDICAL_RECORDS_BY_KEY.get(row.patient_key, 0)
            if row.legacy_medical_records_active != exp_rec:
                reasons.append(
                    f"patient {row.patient_key} legacy medical records "
                    f"{row.legacy_medical_records_active} != expected {exp_rec}",
                )
    if inventory.legacy_measurements_active != EXPECTED_LEGACY_MEASUREMENT_TOTAL:
        reasons.append(
            f"legacy measurement total {inventory.legacy_measurements_active} "
            f"!= {EXPECTED_LEGACY_MEASUREMENT_TOTAL}",
        )
    if inventory.legacy_medical_records_active != EXPECTED_LEGACY_MEDICAL_RECORD_TOTAL:
        reasons.append(
            f"legacy medical record total {inventory.legacy_medical_records_active} "
            f"!= {EXPECTED_LEGACY_MEDICAL_RECORD_TOTAL}",
        )
    if inventory.v2_measurements != 0:
        reasons.append(f"v2 measurements present: {inventory.v2_measurements}")
    if inventory.v2_medical_records != 0:
        reasons.append(f"v2 medical records present: {inventory.v2_medical_records}")
    if inventory.non_task3_measurements != 0:
        reasons.append(f"non-Task3 measurements: {inventory.non_task3_measurements}")
    if inventory.non_task3_medical_records != 0:
        reasons.append(f"non-Task3 medical records: {inventory.non_task3_medical_records}")
    for row in inventory.patient_rows:
        if not row.patient_is_active:
            reasons.append(f"patient {row.patient_key} is not active")
    return GuardCheckResult(ok=not reasons, abort_reasons=tuple(reasons))


@dataclass
class ProtectedCounts:
    appointments: int
    risk_history: int
    assignments: int
    consents: int


@dataclass
class DemoEnrichmentLegacyCleanupResult:
    mode: str
    inventory: LegacyCleanupInventory
    guard: GuardCheckResult
    mutated: bool = False
    deactivated_measurements: int = 0
    deactivated_medical_records: int = 0
    protected_before: ProtectedCounts | None = None
    protected_after: ProtectedCounts | None = None
    post_verify_ok: bool | None = None
    abort_reasons: tuple[str, ...] = ()


def _count_notes_classes(rows: list, classifier) -> dict[str, int]:
    counts = {
        "legacy_active": 0,
        "legacy_deactivated": 0,
        "v2": 0,
        "non_task3": 0,
        "unrelated": 0,
    }
    for row in rows:
        is_active = bool(getattr(row, "is_active", True))
        key = classifier(getattr(row, "notes", None), is_active=is_active)
        if key == "unrelated":
            if is_active:
                key = "non_task3"
            else:
                continue
        if key == "v2" and not is_active:
            continue
        counts[key] += 1
    return counts


async def _load_org_patients(
    patient_repository: PatientRepository,
    organization_id: UUID,
) -> list[Patient]:
    return await patient_repository.list_by_organization_ids(
        [organization_id],
        offset=0,
        limit=500,
    )


async def build_legacy_cleanup_inventory(
    *,
    patient_repository: PatientRepository,
    measurement_repository: HealthMeasurementRepository,
    medical_record_repository: MedicalRecordRepository,
    appointment_repository: AppointmentRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    assignment_repository: PatientAssignmentRepository,
    consent_repository: PatientConsentRepository,
    organization_id: UUID,
    verify_production_patient_ids: bool,
) -> LegacyCleanupInventory:
    org_patients = await _load_org_patients(patient_repository, organization_id)
    inventory = LegacyCleanupInventory()
    inventory.notes.append(A1_RISK_HISTORY_INVENTORY_NOTE)

    for spec in PATIENT_SPECS:
        patient = _find_demo_patient_in_org(
            org_patients,
            marker=spec.marker,
            first_name=spec.first_name,
            last_name=spec.last_name,
            date_of_birth=spec.date_of_birth,
        )
        if patient is None:
            continue
        marker_ok = patient_marker_matches(patient, spec.marker)
        if verify_production_patient_ids:
            expected_id = EXPECTED_PRODUCTION_PATIENT_IDS.get(spec.key)
            if expected_id is not None and patient.id != expected_id:
                marker_ok = False

        measurements = await measurement_repository.list_by_owner(
            patient.owner_id,
            patient_id=patient.id,
            limit=500,
            include_inactive=True,
        )
        records = await medical_record_repository.list_by_owner(
            patient.owner_id,
            patient_id=patient.id,
            limit=500,
            include_inactive=True,
        )
        meas_counts = _count_notes_classes(measurements, classify_measurement_notes)
        rec_counts = _count_notes_classes(records, classify_medical_record_notes)

        appointments = await appointment_repository.list_by_owner(
            patient.owner_id,
            patient_id=patient.id,
            limit=200,
        )
        risk_count = await risk_history_repository.count_by_patient(patient.id)
        assignments = await assignment_repository.list_by_patient_and_organization(
            patient.id,
            organization_id,
        )
        consents = await consent_repository.list_by_patient_and_organization(
            patient.id,
            organization_id,
        )

        row = PatientLegacyInventory(
            patient_key=spec.key,
            patient_id=patient.id,
            marker_ok=marker_ok,
            legacy_measurements_active=meas_counts["legacy_active"],
            legacy_measurements_deactivated=meas_counts["legacy_deactivated"],
            legacy_medical_records_active=rec_counts["legacy_active"],
            legacy_medical_records_deactivated=rec_counts["legacy_deactivated"],
            v2_measurements=meas_counts["v2"],
            v2_medical_records=rec_counts["v2"],
            non_task3_measurements=meas_counts["non_task3"],
            non_task3_medical_records=rec_counts["non_task3"],
            appointments=len(appointments),
            risk_history=risk_count,
            assignments=len(assignments),
            consents=len(consents),
            patient_is_active=patient.is_active,
        )
        inventory.patient_rows.append(row)

    return inventory


async def _protected_totals(inventory: LegacyCleanupInventory) -> ProtectedCounts:
    return ProtectedCounts(
        appointments=sum(r.appointments for r in inventory.patient_rows),
        risk_history=sum(r.risk_history for r in inventory.patient_rows),
        assignments=sum(r.assignments for r in inventory.patient_rows),
        consents=sum(r.consents for r in inventory.patient_rows),
    )


def _protected_unchanged(before: ProtectedCounts, after: ProtectedCounts) -> bool:
    return (
        before.appointments == after.appointments
        and before.risk_history == after.risk_history
        and before.assignments == after.assignments
        and before.consents == after.consents
    )


async def analyze_demo_enrichment_legacy_cleanup(
    *,
    organization_repository: OrganizationRepository,
    patient_repository: PatientRepository,
    measurement_repository: HealthMeasurementRepository,
    medical_record_repository: MedicalRecordRepository,
    appointment_repository: AppointmentRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    assignment_repository: PatientAssignmentRepository,
    consent_repository: PatientConsentRepository,
    config: DemoEnrichmentLegacyCleanupConfig | None = None,
) -> DemoEnrichmentLegacyCleanupResult:
    cfg = config or DemoEnrichmentLegacyCleanupConfig()
    organization = await organization_repository.get_by_slug(cfg.organization_slug)
    if organization is None:
        msg = f"Organization slug {cfg.organization_slug!r} not found."
        raise ValueError(msg)
    if organization.slug != DEMO_ORGANIZATION_SLUG:
        msg = f"Refusing cleanup: expected slug {DEMO_ORGANIZATION_SLUG!r}."
        raise ValueError(msg)

    inventory = await build_legacy_cleanup_inventory(
        patient_repository=patient_repository,
        measurement_repository=measurement_repository,
        medical_record_repository=medical_record_repository,
        appointment_repository=appointment_repository,
        risk_history_repository=risk_history_repository,
        assignment_repository=assignment_repository,
        consent_repository=consent_repository,
        organization_id=organization.id,
        verify_production_patient_ids=cfg.verify_production_patient_ids,
    )
    guard = validate_pre_cleanup_guards(
        inventory,
        strict_production_ids=cfg.verify_production_patient_ids,
    )
    return DemoEnrichmentLegacyCleanupResult(
        mode="analyze",
        inventory=inventory,
        guard=guard,
        mutated=False,
    )


async def run_demo_enrichment_legacy_cleanup(
    *,
    organization_repository: OrganizationRepository,
    patient_repository: PatientRepository,
    measurement_repository: HealthMeasurementRepository,
    medical_record_repository: MedicalRecordRepository,
    appointment_repository: AppointmentRepository,
    risk_history_repository: RiskAssessmentHistoryRepository,
    assignment_repository: PatientAssignmentRepository,
    consent_repository: PatientConsentRepository,
    config: DemoEnrichmentLegacyCleanupConfig | None = None,
    confirm_cleanup: bool = False,
) -> DemoEnrichmentLegacyCleanupResult:
    """Analyze by default; deactivate legacy rows only when confirm_cleanup=True."""
    cfg = config or DemoEnrichmentLegacyCleanupConfig()
    organization = await organization_repository.get_by_slug(cfg.organization_slug)
    if organization is None:
        msg = f"Organization slug {cfg.organization_slug!r} not found."
        raise ValueError(msg)

    inventory = await build_legacy_cleanup_inventory(
        patient_repository=patient_repository,
        measurement_repository=measurement_repository,
        medical_record_repository=medical_record_repository,
        appointment_repository=appointment_repository,
        risk_history_repository=risk_history_repository,
        assignment_repository=assignment_repository,
        consent_repository=consent_repository,
        organization_id=organization.id,
        verify_production_patient_ids=cfg.verify_production_patient_ids,
    )
    guard = validate_pre_cleanup_guards(
        inventory,
        strict_production_ids=cfg.verify_production_patient_ids,
    )

    if not confirm_cleanup:
        return DemoEnrichmentLegacyCleanupResult(
            mode="analyze",
            inventory=inventory,
            guard=guard,
            mutated=False,
        )

    if not guard.ok:
        return DemoEnrichmentLegacyCleanupResult(
            mode="cleanup_aborted",
            inventory=inventory,
            guard=guard,
            mutated=False,
            abort_reasons=guard.abort_reasons,
        )

    protected_before = await _protected_totals(inventory)
    org_patients = await _load_org_patients(patient_repository, organization.id)
    deactivated_meas = 0
    deactivated_rec = 0

    for spec in PATIENT_SPECS:
        patient = _find_demo_patient_in_org(
            org_patients,
            marker=spec.marker,
            first_name=spec.first_name,
            last_name=spec.last_name,
            date_of_birth=spec.date_of_birth,
        )
        if patient is None:
            continue
        measurements = await measurement_repository.list_by_owner(
            patient.owner_id,
            patient_id=patient.id,
            limit=500,
        )
        for row in measurements:
            if classify_measurement_notes(row.notes, is_active=row.is_active) != "legacy_active":
                continue
            soft_deactivate_clinical_child(row)
            await measurement_repository.update(row)
            deactivated_meas += 1

        records = await medical_record_repository.list_by_owner(
            patient.owner_id,
            patient_id=patient.id,
            limit=500,
        )
        for row in records:
            if classify_medical_record_notes(row.notes, is_active=row.is_active) != "legacy_active":
                continue
            soft_deactivate_clinical_child(row)
            await medical_record_repository.update(row)
            deactivated_rec += 1

    after_inventory = await build_legacy_cleanup_inventory(
        patient_repository=patient_repository,
        measurement_repository=measurement_repository,
        medical_record_repository=medical_record_repository,
        appointment_repository=appointment_repository,
        risk_history_repository=risk_history_repository,
        assignment_repository=assignment_repository,
        consent_repository=consent_repository,
        organization_id=organization.id,
        verify_production_patient_ids=False,
    )
    protected_after = await _protected_totals(after_inventory)
    post_ok = (
        after_inventory.legacy_measurements_active == 0
        and after_inventory.legacy_medical_records_active == 0
        and after_inventory.v2_measurements == 0
        and after_inventory.v2_medical_records == 0
        and _protected_unchanged(protected_before, protected_after)
        and all(row.patient_is_active for row in after_inventory.patient_rows)
    )

    return DemoEnrichmentLegacyCleanupResult(
        mode="cleanup",
        inventory=after_inventory,
        guard=guard,
        mutated=True,
        deactivated_measurements=deactivated_meas,
        deactivated_medical_records=deactivated_rec,
        protected_before=protected_before,
        protected_after=protected_after,
        post_verify_ok=post_ok,
    )


def enrichment_marker_keys_for_tests() -> tuple[str, ...]:
    return ENRICHMENT_MARKERS
