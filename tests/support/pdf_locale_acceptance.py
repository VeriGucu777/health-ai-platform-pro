"""Acceptance checks for patient health PDF language (product criteria, not copy-module mirrors)."""

from __future__ import annotations

import re

from tests.support.pdf_report_helpers import normalize_pdf_text

# User-reported English leaks that must never appear in Turkish PDFs.
ENGLISH_PHRASES_FORBIDDEN_IN_TURKISH_PDF = (
    "No blood glucose measurements were recorded in the selected date range.",
    "No systolic blood pressure measurements were recorded in the selected date range.",
    "No diastolic blood pressure measurements were recorded in the selected date range.",
    "No resting heart rate measurements were recorded in the selected date range.",
    "No weight measurements were recorded in the selected date range.",
    "Add more health measurements over time to generate meaningful insights.",
    "Clinical insights and health alerts are informational tracking summaries only",
    "This patient health report is an informational summary generated from recorded data",
    "Patient Health Report",
    "Patient information",
    "Follow-up recommendations",
    "Medical disclaimer",
    "Clinical insights",
    "qualified healthcare professional",
    "Prompt professional evaluation should be considered",
    "informational summary generated from recorded data",
    "not a diagnosis and do not replace evaluation",
    "official clinical document",
)

TURKISH_SECTION_MARKERS = (
    "Hasta Sağlık Raporu",
    "Hasta bilgileri",
    "Klinik içgörüler",
    "Tıbbi sorumluluk reddi",
)

ENGLISH_SECTION_MARKERS = (
    "Patient Health Report",
    "Patient information",
    "Clinical insights",
    "Medical disclaimer",
)

INTERNAL_NOTE_MARKERS = (
    "seed:",
    "SEED:",
    "demo-live-policy",
    "demo-fixture:",
    "internal-test:",
)

_TR_MONTH = re.compile(r"\b\d{1,2}\s+(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)\s+\d{4}")
_EN_MONTH = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}"
)

_RAW_GENDER_ENUM = re.compile(r"\b(female|male)\b", re.IGNORECASE)
_RAW_SEVERITY_INFO = re.compile(r"\|\s*info\s*\|", re.IGNORECASE)


def find_english_leaks_in_turkish_pdf(text: str) -> list[str]:
    return [phrase for phrase in ENGLISH_PHRASES_FORBIDDEN_IN_TURKISH_PDF if phrase in text]


def assert_turkish_pdf_meets_locale_acceptance(text: str) -> None:
    """Turkish UI locale: monolingual Turkish user-facing report content."""
    turkish_hits = sum(1 for marker in TURKISH_SECTION_MARKERS if marker in text)
    assert turkish_hits >= 2, "Expected multiple Turkish section markers in PDF text"
    leaks = find_english_leaks_in_turkish_pdf(text)
    assert not leaks, f"English phrases in Turkish PDF: {leaks}"
    for marker in INTERNAL_NOTE_MARKERS:
        assert marker not in text, f"Internal marker leaked into PDF: {marker}"


def assert_english_pdf_meets_locale_acceptance(text: str) -> None:
    """English UI locale: monolingual English user-facing report content."""
    english_hits = sum(1 for marker in ENGLISH_SECTION_MARKERS if marker in text)
    assert english_hits >= 2, "Expected multiple English section markers in PDF text"
    for marker in TURKISH_SECTION_MARKERS:
        assert marker not in text, f"Turkish section marker leaked into English PDF: {marker}"


def assert_pdf_text_differs_by_locale(tr_text: str, en_text: str) -> None:
    assert normalize_pdf_text(tr_text) != normalize_pdf_text(en_text)


def assert_turkish_date_style_present(text: str) -> None:
    assert _TR_MONTH.search(text), "Expected Turkish-style month abbreviation in PDF dates"


def assert_english_date_style_present(text: str) -> None:
    assert _EN_MONTH.search(text), "Expected English-style month abbreviation in PDF dates"


def verify_turkish_pdf_output(text: str) -> dict[str, str]:
    """Product verification flags for a Turkish PDF text extract (YES = problem detected)."""
    leaks = find_english_leaks_in_turkish_pdf(text)
    internal_leak = any(marker in text for marker in INTERNAL_NOTE_MARKERS)
    enum_leak = bool(_RAW_GENDER_ENUM.search(text) or _RAW_SEVERITY_INFO.search(text))
    date_ok = _TR_MONTH.search(text) is not None
    return {
        "english_leakage": "YES" if leaks else "NO",
        "english_leak_phrases": ", ".join(leaks[:5]) if leaks else "",
        "internal_marker_leakage": "YES" if internal_leak else "NO",
        "enum_localized": "NO" if enum_leak else "YES",
        "date_localized": "YES" if date_ok else "NO",
    }


def verify_english_pdf_output(text: str) -> dict[str, str]:
    turkish_leak = any(marker in text for marker in TURKISH_SECTION_MARKERS)
    internal_leak = any(marker in text for marker in INTERNAL_NOTE_MARKERS)
    enum_leak = bool(re.search(r"\b(Kadın|Erkek|Pasif|Aktif)\b", text))
    date_ok = _EN_MONTH.search(text) is not None
    return {
        "turkish_leakage": "YES" if turkish_leak else "NO",
        "internal_marker_leakage": "YES" if internal_leak else "NO",
        "enum_localized": "NO" if enum_leak else "YES",
        "date_localized": "YES" if date_ok else "NO",
    }
