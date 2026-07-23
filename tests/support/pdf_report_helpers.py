"""Shared helpers for patient health PDF report tests."""

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def normalize_pdf_text(text: str) -> str:
    return " ".join(text.split())


def assert_disclaimers_present(pdf_bytes: bytes, text: str | None = None) -> None:
    content = text if text is not None else extract_pdf_text(pdf_bytes)
    normalized = normalize_pdf_text(content)
    assert "Clinical insights and health alerts are informational tracking summaries only." in normalized
    assert "not a diagnosis" in normalized
    assert "qualified healthcare professional" in normalized
    assert "official clinical document" in normalized
    assert "informational summary generated from recorded data" in normalized


def assert_turkish_content_present(pdf_bytes: bytes, text: str | None = None) -> None:
    content = text if text is not None else extract_pdf_text(pdf_bytes)
    assert "Hasta Bilgileri" in content or "Hasta Sa" in content
    assert b"/ToUnicode" in pdf_bytes or "NotoSans" in pdf_bytes.decode("latin-1", errors="ignore")
