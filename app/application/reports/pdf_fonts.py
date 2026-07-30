"""Centralized PDF Unicode font resolution and ReportLab registration."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.exceptions import AppException

PDF_FONT_FILENAME = "NotoSans-Regular.ttf"
PDF_FONT_LICENSE_FILENAME = "OFL.txt"
PDF_FONT_NAME = "NotoSans"
PDF_FONTS_DIR = "assets/fonts"


class PdfFontUnavailableError(AppException):
    """Raised when the bundled Unicode PDF font is missing or unreadable."""

    def __init__(
        self,
        message: str = "PDF generation is temporarily unavailable.",
        *,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, status_code=503, details=details or {})


def resolve_pdf_font_path() -> Path:
    """Return the project-local path to the bundled NotoSans Regular TTF."""
    app_root = Path(__file__).resolve().parents[2]
    return app_root / PDF_FONTS_DIR / PDF_FONT_FILENAME


def resolve_pdf_font_license_path() -> Path:
    """Return the project-local path to the bundled OFL license notice."""
    app_root = Path(__file__).resolve().parents[2]
    return app_root / PDF_FONTS_DIR / PDF_FONT_LICENSE_FILENAME


def validate_pdf_font_available(font_path: Path | None = None) -> Path:
    """Verify the Unicode PDF font file exists before registration."""
    path = font_path or resolve_pdf_font_path()
    if not path.is_file():
        raise PdfFontUnavailableError(
            "PDF generation is temporarily unavailable because the required Unicode "
            "font asset is missing.",
            details={
                "expected_filename": PDF_FONT_FILENAME,
                "expected_relative_path": f"app/{PDF_FONTS_DIR}/{PDF_FONT_FILENAME}",
                "license_relative_path": f"app/{PDF_FONTS_DIR}/{PDF_FONT_LICENSE_FILENAME}",
            },
        )
    return path


def ensure_pdf_unicode_font_registered() -> str:
    """Register the bundled Unicode font once and return its ReportLab name."""
    font_path = validate_pdf_font_available()
    if PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(font_path)))
    return PDF_FONT_NAME
