"""Sanitize MedicalRecord text and build presentation keys for clinical summary."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.entities.medical_record import MedicalRecord

_SEED_MARKER_PATTERN = re.compile(r"seed:[^\s]+", re.IGNORECASE)
_DEMO_PHRASE_PATTERNS = (
    re.compile(r"\(?\s*synthetic[^.;)]*[.;)]?\s*", re.IGNORECASE),
    re.compile(r"\(?\s*fictional[^.;)]*[.;)]?\s*", re.IGNORECASE),
    re.compile(r"\(?\s*demo values[^.;)]*[.;)]?\s*", re.IGNORECASE),
    re.compile(r"decision-support review only\.?", re.IGNORECASE),
    re.compile(r"for chart review[^.;]*[.;]?", re.IGNORECASE),
    re.compile(r"not a prescribing instruction[^.;]*[.;]?", re.IGNORECASE),
    re.compile(r"\(demo\)", re.IGNORECASE),
    re.compile(r"\bdemo\b", re.IGNORECASE),
    re.compile(r"synthetic demo[^.;]*[.;]?", re.IGNORECASE),
)

_LDL_PATTERN = re.compile(r"ldl\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mg/dl", re.IGNORECASE)
_HDL_PATTERN = re.compile(r"hdl\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mg/dl", re.IGNORECASE)
_TG_PATTERN = re.compile(
    r"(?:triglycerides?|tg)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mg/dl",
    re.IGNORECASE,
)
_HBA1C_PATTERN = re.compile(
    r"(?:hb\s*?a1c|hba1c|a1c)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LipidPanelValues:
    ldl: str
    hdl: str
    triglycerides: str | None = None


def sanitize_clinical_summary_text(value: str) -> str:
    """Remove internal demo markers while preserving numeric clinical values."""
    cleaned = _SEED_MARKER_PATTERN.sub("", value)
    for pattern in _DEMO_PHRASE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = cleaned.replace(";;", ";").replace(" ;", ";")
    return " ".join(cleaned.split()).strip(" ;.")


def extract_hba1c_value(text: str) -> str | None:
    """Parse HbA1c percent when present in lab or visit text."""
    match = _HBA1C_PATTERN.search(text)
    if match is None:
        return None
    return match.group(1).replace(",", ".").strip()


def extract_lipid_panel_values(text: str) -> LipidPanelValues | None:
    """Parse LDL/HDL/triglycerides when all required lipid fields are present."""
    ldl_match = _LDL_PATTERN.search(text)
    hdl_match = _HDL_PATTERN.search(text)
    if ldl_match is None or hdl_match is None:
        return None
    tg_match = _TG_PATTERN.search(text)
    return LipidPanelValues(
        ldl=ldl_match.group(1),
        hdl=hdl_match.group(1),
        triglycerides=tg_match.group(1) if tg_match else None,
    )


def record_text_blob(record: MedicalRecord) -> str:
    return " ".join(
        part
        for part in (record.title, record.diagnosis, record.description, record.treatment, record.medications)
        if part
    )


def is_echocardiography_record(record: MedicalRecord) -> bool:
    blob = record_text_blob(record).lower()
    return any(token in blob for token in ("echocardiograph", "ekokardiyografi", "echo cardi"))


def is_brain_imaging_record(record: MedicalRecord) -> bool:
    blob = record_text_blob(record).lower()
    return any(token in blob for token in ("brain", "beyin", "neuroimaging"))


def sanitized_medication_or_treatment(record: MedicalRecord) -> str:
    meds = sanitize_clinical_summary_text((record.medications or "").strip())
    treatment = sanitize_clinical_summary_text((record.treatment or "").strip())
    if meds and treatment and treatment not in meds:
        return sanitize_clinical_summary_text(f"{meds}; {treatment}")
    return meds or treatment


def is_documented_diabetes_medication_plan(record: MedicalRecord) -> bool:
    """Detect diabetes medication documentation without inventing new content."""
    blob = sanitized_medication_or_treatment(record).lower()
    if not blob:
        return False
    return any(
        token in blob
        for token in (
            "metformin",
            "insulin",
            "glimepiride",
            "sitagliptin",
            "empagliflozin",
            "semaglutide",
        )
    )


def is_stroke_neurology_follow_up_record(record: MedicalRecord) -> bool:
    """Visit records that document neurological / post-stroke follow-up."""
    blob = record_text_blob(record).lower()
    return any(
        token in blob
        for token in (
            "neurology",
            "nöroloji",
            "hemipares",
            "stroke follow",
            "inme",
            "post-stroke",
            "post stroke",
        )
    )


def is_documented_stroke_secondary_prevention_plan(record: MedicalRecord) -> bool:
    """Detect antiplatelet/statin or documented secondary stroke prevention plans."""
    blob = sanitized_medication_or_treatment(record).lower()
    if not blob:
        return False
    return any(
        token in blob
        for token in (
            "antiplatelet",
            "statin",
            "secondary stroke",
            "secondary prevention",
            "sekonder",
            "clopidogrel",
            "aspirin",
        )
    )


def is_documented_diabetes_monitoring_care_plan(text: str) -> bool:
    """Detect home glucose / HbA1c / lifestyle follow-up plans in recorded text."""
    cleaned = sanitize_clinical_summary_text(text).lower()
    if not cleaned:
        return False
    has_glucose_monitoring = any(
        token in cleaned
        for token in (
            "home glucose",
            "glucose logging",
            "evde kan şekeri",
            "kan şekeri takibi",
        )
    )
    has_hba1c_follow = "hba1c" in cleaned or "a1c" in cleaned or "quarterly" in cleaned
    has_lifestyle = (
        "lifestyle" in cleaned or "yaşam tarz" in cleaned or "counseling" in cleaned
    )
    return has_glucose_monitoring and has_hba1c_follow and has_lifestyle


def is_documented_cardiac_monitoring_care_plan(text: str) -> bool:
    """Detect blood-pressure/lipid/activity follow-up plans without inventing new content."""
    cleaned = sanitize_clinical_summary_text(text).lower()
    if not cleaned:
        return False
    has_blood_pressure = "blood pressure" in cleaned or "kan basınc" in cleaned
    has_lipid_follow_up = "lipid recheck" in cleaned or (
        "lipid" in cleaned and ("recheck" in cleaned or "month" in cleaned)
    )
    has_activity = "activity" in cleaned or "aktivite" in cleaned or "guidance" in cleaned
    return has_blood_pressure and has_lipid_follow_up and has_activity
