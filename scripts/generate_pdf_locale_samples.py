"""Generate TR/EN sample PDFs via the FastAPI app and print verification flags."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.support.pdf_locale_acceptance import (  # noqa: E402
    verify_english_pdf_output,
    verify_turkish_pdf_output,
)
from tests.support.pdf_report_helpers import extract_pdf_text  # noqa: E402

REPORT_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"
OUTPUT_DIR = ROOT / "tmp" / "pdf_locale_samples"


async def _register_and_login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Demo",
            "last_name": "Doctor",
            "role": "doctor",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    get_settings.cache_clear()
    app = create_app(Settings(environment="test"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_login(client, "pdf-locale-sample@example.com")
        create = await client.post(
            "/api/v1/patients",
            json={
                "first_name": "Ayşe",
                "last_name": "Demo",
                "date_of_birth": "1990-06-12",
                "gender": "female",
                "notes": "seed:demo-live-policy-patient-v1",
            },
            headers=headers,
        )
        create.raise_for_status()
        patient_id = create.json()["id"]

        await client.post(
            "/api/v1/health-measurements",
            json={
                "patient_id": patient_id,
                "measured_at": "2026-08-10T08:00:00Z",
                "blood_glucose": 200,
                "glucose_context": "fasting",
            },
            headers=headers,
        )

        tr_path = OUTPUT_DIR / f"patient-{patient_id}-tr.pdf"
        en_path = OUTPUT_DIR / f"patient-{patient_id}-en.pdf"

        tr_resp = await client.get(
            f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?"
            f"{REPORT_RANGE}&locale=tr",
            headers=headers,
        )
        en_resp = await client.get(
            f"/api/v1/patients/{patient_id}/reports/health-summary.pdf?"
            f"{REPORT_RANGE}&locale=en",
            headers=headers,
        )
        tr_resp.raise_for_status()
        en_resp.raise_for_status()

        tr_path.write_bytes(tr_resp.content)
        en_path.write_bytes(en_resp.content)

        tr_text = extract_pdf_text(tr_resp.content)
        en_text = extract_pdf_text(en_resp.content)
        report = {
            "patient_id": patient_id,
            "tr_pdf": str(tr_path),
            "en_pdf": str(en_path),
            "tr_verification": verify_turkish_pdf_output(tr_text),
            "en_verification": verify_english_pdf_output(en_text),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
