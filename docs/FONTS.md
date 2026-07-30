# PDF Font Assets

Patient health summary PDF reports require a **project-local Unicode font** bundled with the backend. The application does not download fonts at runtime and does not rely on operating-system font paths.

## Required Files

| File | Path | Purpose |
|---|---|---|
| `NotoSans-Regular.ttf` | `backend/app/assets/fonts/NotoSans-Regular.ttf` | Unicode PDF rendering (English + Turkish) |
| `OFL.txt` | `backend/app/assets/fonts/OFL.txt` | SIL Open Font License 1.1 notice |

Both files must be present in git checkouts used for development, CI, and production deployment.

## License

`NotoSans-Regular.ttf` is distributed under the **SIL Open Font License 1.1**. The full license notice must remain in `app/assets/fonts/OFL.txt` whenever the font file is bundled with the application.

Obtain the font only from an official Noto source if you need to replace or verify the binary. **Do not commit unverified or randomly downloaded font files.**

## Runtime Behavior

PDF generation uses `app/application/reports/pdf_fonts.py`:

1. Resolve `app/assets/fonts/NotoSans-Regular.ttf` relative to the application package root.
2. Fail with **HTTP 503** (`PdfFontUnavailableError`) if the font file is missing.
3. Register the font once per process with ReportLab and embed Unicode subsets in generated PDFs.

There is **no fallback** to Helvetica or system fonts. Missing fonts must be treated as a deployment/configuration error, not silently ignored.

## Development

After cloning the repository:

```powershell
cd backend
Test-Path app/assets/fonts/NotoSans-Regular.ttf
Test-Path app/assets/fonts/OFL.txt
```

If the font file is missing, PDF report endpoints return **503** with a safe error message. Place the licensed `NotoSans-Regular.ttf` file at the path above and keep `OFL.txt` alongside it.

## CI

GitHub Actions verifies both files exist before unit/API tests run. PDF tests also exercise Turkish and English content extraction where the bundled font is available.

## Production (Render/Linux)

The font ships with the repository checkout. No extra Render configuration is required when the file is present in the deployed commit.

Ensure deployment uses a full git checkout of `backend/` — sparse checkouts that omit `app/assets/fonts/` will break PDF generation.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| HTTP 503 on PDF download | Font file missing from deploy | Verify `app/assets/fonts/NotoSans-Regular.ttf` exists on the instance |
| CI fails at font asset step | Font not committed or path changed | Restore font + `OFL.txt` at expected paths |
| Turkish characters show as boxes | Wrong/missing font file | Replace with licensed Noto Sans Regular TTF |
| Tests fail Turkish extraction | pypdf extraction limitation or missing font | Confirm font file exists; inspect PDF bytes for `/ToUnicode` |

## Text Extraction Limitation

Automated tests use `pypdf` to extract text from generated PDFs. Extraction may normalize or reorder glyphs compared to a PDF viewer. Tests therefore combine:

- Extracted text checks for Turkish and English sample words
- Byte-level checks for embedded Unicode font markers (`/ToUnicode`, `NotoSans`)

Viewer-perfect glyph assertions are intentionally avoided to reduce brittle failures.

## Related Code

| Module | Responsibility |
|---|---|
| `app/application/reports/pdf_fonts.py` | Font path resolution, validation, registration |
| `app/application/reports/patient_health_pdf_builder.py` | ReportLab PDF layout |
| `tests/unit/test_pdf_fonts.py` | Font resolver tests |
| `tests/unit/test_patient_health_pdf_builder.py` | Builder Unicode tests |
| `tests/api/test_patient_health_reports.py` | Endpoint compatibility tests |
