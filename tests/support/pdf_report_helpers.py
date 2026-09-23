"""Shared helpers for patient health PDF report tests."""

from io import BytesIO

from pypdf import PdfReader

# Turkish samples used across PDF tests. pypdf text extraction may reorder or
# normalize some glyphs; tests combine extracted text with PDF byte markers.
TURKISH_ALPHABET_SAMPLES = "ÇĞİÖŞÜıçğöşü"
TURKISH_FIXTURE_WORDS = (
    "Şahin",
    "Öğüt",
    "Kan şekeri",
    "Sağlık",
    "içgörü",
    "Türkçe",
    "Seçilen",
    "Doğum",
)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def normalize_pdf_text(text: str) -> str:
    return " ".join(text.split())


def assert_pdf_has_unicode_font_embedding(pdf_bytes: bytes) -> None:
    """Verify the PDF embeds a Unicode-capable font subset."""
    assert pdf_bytes.startswith(b"%PDF")
    latin1_view = pdf_bytes.decode("latin-1", errors="ignore")
    assert b"/Font" in pdf_bytes
    assert "/ToUnicode" in latin1_view or "NotoSans" in latin1_view


def assert_turkish_content_present(pdf_bytes: bytes, text: str | None = None) -> None:
    """Assert Turkish section labels and sample words appear in the PDF."""
    content = text if text is not None else extract_pdf_text(pdf_bytes)
    assert_pdf_has_unicode_font_embedding(pdf_bytes)

    matched_words = [word for word in TURKISH_FIXTURE_WORDS if word in content]
    assert matched_words, (
        "Expected at least one Turkish fixture word in extracted PDF text. "
        f"Checked: {', '.join(TURKISH_FIXTURE_WORDS)}"
    )

    matched_letters = [letter for letter in TURKISH_ALPHABET_SAMPLES if letter in content]
    assert len(matched_letters) >= 4, (
        "Expected multiple Turkish alphabet letters in extracted PDF text. "
        f"Found: {matched_letters or 'none'}"
    )


def assert_english_content_present(text: str) -> None:
    """Assert English report content is present."""
    normalized = normalize_pdf_text(text)
    assert "Health AI Platform Pro" in normalized
    assert "Patient Health Report" in normalized
    assert "not a diagnosis" in normalized
    assert "qualified healthcare professional" in normalized


def assert_turkish_disclaimers_present(text: str) -> None:
    normalized = normalize_pdf_text(text)
    assert "Klinik" in normalized and "içgörü" in normalized
    assert "Bu hasta sağlık raporu" in normalized
    assert "değildir" in normalized
    assert "Tanı" in normalized or "tanı" in normalized


def assert_disclaimers_present(
    pdf_bytes: bytes,
    text: str | None = None,
    *,
    locale: str = "en",
) -> None:
    content = text if text is not None else extract_pdf_text(pdf_bytes)
    if locale == "tr":
        assert_turkish_disclaimers_present(content)
        return
    normalized = normalize_pdf_text(content)
    assert (
        "Clinical insights and health alerts are informational tracking summaries only."
        in normalized
    )
    assert "not a diagnosis" in normalized
    assert "qualified healthcare professional" in normalized
    assert "official clinical document" in normalized
    assert "informational summary generated from recorded data" in normalized
