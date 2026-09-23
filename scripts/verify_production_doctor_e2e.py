#!/usr/bin/env python3
"""Production doctor E2E checks (no secrets printed)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = os.getenv("PRODUCTION_API_BASE", "https://health-ai-platform-pro.onrender.com").rstrip("/")
DOCTOR_EMAIL = os.getenv("DEMO_DOCTOR_EMAIL", "doctor.demo1@gmail.com")
DOCTOR_PASSWORD = os.getenv("DEMO_DOCTOR_PASSWORD", "Demo12345!")
ASSIGNED_PATIENT_ID = os.getenv(
    "DEMO_ASSIGNED_PATIENT_ID",
    "aa15a20b-56a1-4cad-9bb5-d2ac9939ec99",
)
UNASSIGNED_PATIENT_ID = os.getenv(
    "DEMO_UNASSIGNED_PATIENT_ID",
    "5550d052-471e-40e3-b978-95b465e4c468",
)


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    url = f"{BASE}{path}"
    hdrs = dict(headers or {})
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def main() -> int:
    results: dict[str, str] = {}

    status, _, _ = _request("GET", "/api/v1/health")
    results["health"] = str(status)

    login_status, _, login_body = _request(
        "POST",
        "/api/v1/auth/login",
        body={"email": DOCTOR_EMAIL, "password": DOCTOR_PASSWORD},
    )
    results["doctor_login"] = str(login_status)
    if login_status != 200:
        print(json.dumps(results, indent=2))
        return 1

    payload = json.loads(login_body.decode("utf-8"))
    token = payload.get("access_token") or payload.get("token")
    if not token:
        results["doctor_login"] = "200_no_token"
        print(json.dumps(results, indent=2))
        return 1

    me_status, _, me_body = _request("GET", "/api/v1/auth/me", token=token)
    results["auth_me"] = str(me_status)
    me = json.loads(me_body.decode("utf-8")) if me_status == 200 else {}
    results["doctor_role"] = str(me.get("role", ""))

    list_status, _, list_body = _request("GET", "/api/v1/patients", token=token)
    results["patients_list"] = str(list_status)
    patient_ids: set[str] = set()
    if list_status == 200:
        listed = json.loads(list_body.decode("utf-8"))
        items = listed.get("items") or listed.get("patients") or listed
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    patient_ids.add(str(item["id"]))

    results["assigned_patient_visible"] = str(ASSIGNED_PATIENT_ID in patient_ids)
    results["unassigned_patient_hidden"] = str(UNASSIGNED_PATIENT_ID not in patient_ids)

    hub_status, _, _ = _request(
        "GET",
        f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/clinical-summary",
        token=token,
    )
    results["assigned_hub_clinical_summary"] = str(hub_status)

    unassigned_status, _, _ = _request(
        "GET",
        f"/api/v1/patients/{UNASSIGNED_PATIENT_ID}",
        token=token,
    )
    results["unassigned_patient_get"] = str(unassigned_status)

    for loc, accept in (("tr", "tr-TR,tr;q=0.9"), ("en", "en-US,en;q=0.9")):
        pdf_status, pdf_hdrs, pdf_bytes = _request(
            "GET",
            f"/api/v1/patients/{ASSIGNED_PATIENT_ID}/reports/health-summary.pdf?locale={loc}",
            token=token,
            headers={"Accept-Language": accept},
        )
        results[f"pdf_{loc}_status"] = str(pdf_status)
        lower_hdrs = {k.lower(): v for k, v in pdf_hdrs.items()}
        results[f"pdf_{loc}_locale_header"] = lower_hdrs.get("x-report-locale", "")
        ct = pdf_hdrs.get("Content-Type", "")
        results[f"pdf_{loc}_content_type"] = ct.split(";")[0] if ct else ""
        results[f"pdf_{loc}_bytes"] = str(len(pdf_bytes) if pdf_status == 200 else 0)

    mgmt_status, _, _ = _request(
        "GET",
        "/api/v1/organizations/me/membership",
        token=token,
    )
    results["management_api_membership"] = str(mgmt_status)

    print(json.dumps(results, indent=2))
    ok = (
        login_status == 200
        and me.get("role") == "doctor"
        and ASSIGNED_PATIENT_ID in patient_ids
        and UNASSIGNED_PATIENT_ID not in patient_ids
        and hub_status == 200
        and unassigned_status in (403, 404)
        and results.get("pdf_tr_status") == "200"
        and results.get("pdf_tr_locale_header") == "tr"
        and results.get("pdf_en_status") == "200"
        and results.get("pdf_en_locale_header") == "en"
        and mgmt_status in (403, 404)
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
