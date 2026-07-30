"""Unit tests for centralized PDF font resolution and registration."""

from pathlib import Path

import pytest

from app.application.reports.pdf_fonts import (
    PDF_FONT_FILENAME,
    PDF_FONT_LICENSE_FILENAME,
    PDF_FONT_NAME,
    PdfFontUnavailableError,
    ensure_pdf_unicode_font_registered,
    resolve_pdf_font_license_path,
    resolve_pdf_font_path,
    validate_pdf_font_available,
)


def test_resolve_pdf_font_path_points_to_project_local_asset() -> None:
    path = resolve_pdf_font_path()
    assert path.name == PDF_FONT_FILENAME
    assert path.parent.name == "fonts"
    assert path.parent.parent.name == "assets"
    assert path.parents[2].name == "app"


def test_resolve_pdf_font_license_path_points_to_ofl_notice() -> None:
    path = resolve_pdf_font_license_path()
    assert path.name == PDF_FONT_LICENSE_FILENAME
    assert path.parent == resolve_pdf_font_path().parent


def test_validate_pdf_font_available_succeeds_when_font_present() -> None:
    font_path = resolve_pdf_font_path()
    if not font_path.is_file():
        pytest.skip(f"Bundled font not present at {font_path}")

    validated = validate_pdf_font_available()
    assert validated == font_path.resolve()


def test_validate_pdf_font_available_raises_when_font_missing() -> None:
    missing_path = Path("/tmp/health-ai-platform-pro-missing-font.ttf")
    with pytest.raises(PdfFontUnavailableError) as exc_info:
        validate_pdf_font_available(missing_path)

    assert exc_info.value.status_code == 503
    assert exc_info.value.details["expected_filename"] == PDF_FONT_FILENAME
    assert "app/assets/fonts/NotoSans-Regular.ttf" in exc_info.value.details["expected_relative_path"]


def test_ensure_pdf_unicode_font_registered_returns_reportlab_name() -> None:
    font_path = resolve_pdf_font_path()
    if not font_path.is_file():
        pytest.skip(f"Bundled font not present at {font_path}")

    font_name = ensure_pdf_unicode_font_registered()
    assert font_name == PDF_FONT_NAME

    # Registration is cached by ReportLab for the process.
    assert ensure_pdf_unicode_font_registered() == PDF_FONT_NAME
