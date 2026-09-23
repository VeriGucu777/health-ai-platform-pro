"""Locale parsing and date formatting contracts (spec tables, not PDF builder internals)."""

from datetime import UTC, date, datetime

import pytest

from app.application.reports.report_i18n import (
    format_report_date,
    format_report_datetime,
    parse_report_locale,
    resolve_report_locale,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "en"),
        ("en", "en"),
        ("EN", "en"),
        ("tr", "tr"),
        ("TR", "tr"),
        ("", "en"),
        ("   ", "en"),
        ("de", "en"),
        ("fr-CA", "en"),
        ("tr-TR", "en"),
        ("english", "en"),
    ],
)
def test_parse_report_locale_normalizes_supported_values(raw: str | None, expected: str) -> None:
    assert parse_report_locale(raw) == expected


@pytest.mark.parametrize(
    ("value", "locale", "expected_fragment"),
    [
        (date(2026, 9, 23), "tr", "23 Eyl 2026"),
        (date(2026, 9, 23), "en", "Sep 23, 2026"),
        (date(2026, 1, 5), "tr", "5 Oca 2026"),
        (date(2026, 12, 31), "en", "Dec 31, 2026"),
        (date(1990, 6, 12), "tr", "12 Haz 1990"),
        (date(1990, 6, 12), "en", "Jun 12, 1990"),
    ],
)
def test_format_report_date_locale_shapes(
    value: date,
    locale: str,
    expected_fragment: str,
) -> None:
    assert format_report_date(value, locale) == expected_fragment  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("query", "accept_language", "expected"),
    [
        ("tr", None, "tr"),
        (None, "tr-TR,tr;q=0.9", "tr"),
        (None, "en-US,en;q=0.9", "en"),
        ("", "tr-TR", "tr"),
        (None, None, "en"),
        ("de", "tr-TR", "en"),
    ],
)
def test_resolve_report_locale_query_overrides_accept_language(
    query: str | None,
    accept_language: str | None,
    expected: str,
) -> None:
    assert resolve_report_locale(query, accept_language) == expected


def test_format_report_datetime_includes_utc_clock() -> None:
    stamp = datetime(2026, 9, 23, 14, 30, tzinfo=UTC)
    formatted = format_report_datetime(stamp, "en")
    assert "14:30 UTC" in formatted
    assert "Sep" in formatted
