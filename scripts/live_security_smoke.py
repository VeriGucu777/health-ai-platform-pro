#!/usr/bin/env python3
"""Live security smoke (no secrets in stdout).

Clinic admin fixture checks use direct GET by ID and/or page_size=100 list lookup.
Default GET /patients (page_size=20) may omit older demo fixtures when total > 20;
that is not treated as an RBAC failure.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.getenv("PRODUCTION_API_BASE", "https://health-ai-platform-pro.onrender.com").rstrip("/")
DOCTOR_EMAIL = os.getenv("DEMO_DOCTOR_EMAIL", "doctor.demo1@gmail.com")
DOCTOR_PASSWORD = os.getenv("DEMO_DOCTOR_PASSWORD", "Demo12345!")
ADMIN_EMAIL = os.getenv("DEMO_CLINIC_ADMIN_EMAIL", "live-pa-admin-c45d9a48@example.com")
ADMIN_PASSWORD = os.getenv("DEMO_CLINIC_ADMIN_PASSWORD", "LivePolicyE2E1!")
ASSIGNED = os.getenv("DEMO_ASSIGNED_PATIENT_ID", "aa15a20b-56a1-4cad-9bb5-d2ac9939ec99")
UNASSIGNED = os.getenv("DEMO_UNASSIGNED_PATIENT_ID", "5550d052-471e-40e3-b978-95b465e4c468")
ADMIN_LIST_WIDE_PAGE_SIZE = 100


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    url = f"{BASE}{path}"
    hdrs: dict[str, str] = {}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()


def login(email: str, password: str):
    st, _, raw = req("POST", "/api/v1/auth/login", body={"email": email, "password": password})
    if st != 200:
        return st, None, None
    payload = json.loads(raw)
    return st, payload.get("access_token"), payload.get("refresh_token")


def refresh_token(rt: str):
    st, _, raw = req("POST", "/api/v1/auth/refresh", body={"refresh_token": rt})
    if st != 200:
        return st, None, None
    payload = json.loads(raw)
    return st, payload.get("access_token"), payload.get("refresh_token")


def _ids_from_list_body(raw: bytes) -> tuple[set[str], int | None]:
    listed = json.loads(raw)
    items = listed.get("items") if isinstance(listed, dict) else None
    ids: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item["id"]))
    total = listed.get("total") if isinstance(listed, dict) else None
    return ids, int(total) if total is not None else None


def main() -> None:
    out: dict = {}

    st, hdrs, body = req("GET", "/api/v1/health")
    out["health_status"] = st
    if st == 200:
        out["health_json"] = json.loads(body)

    st, _, body = req("GET", "/api/v1/ready")
    out["ready_status"] = st
    if st == 200:
        ready = json.loads(body)
        out["ready_checks"] = ready.get("checks", ready)

    header_keys = (
        "strict-transport-security",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "content-security-policy",
    )
    for key in header_keys:
        out[f"header_{key.replace('-', '_')}"] = hdrs.get(key, "")

    _, hdrs_root, _ = req("GET", "/")
    for key in header_keys:
        if not out.get(f"header_{key.replace('-', '_')}"):
            out[f"header_{key.replace('-', '_')}"] = hdrs_root.get(key, "")

    dl, d_access, _ = login(DOCTOR_EMAIL, DOCTOR_PASSWORD)
    out["doctor_login"] = dl
    if d_access:
        st, _, raw = req("GET", "/api/v1/auth/me", token=d_access)
        out["doctor_me"] = st
        if st == 200:
            out["doctor_role"] = json.loads(raw).get("role")
        st, _, raw = req("GET", "/api/v1/patients", token=d_access)
        out["doctor_patients_list"] = st
        ids, _ = _ids_from_list_body(raw) if st == 200 else (set(), None)
        out["doctor_assigned_in_list"] = ASSIGNED in ids
        out["doctor_unassigned_in_list"] = UNASSIGNED in ids
        out["doctor_assigned_get"] = req("GET", f"/api/v1/patients/{ASSIGNED}", token=d_access)[0]
        out["doctor_unassigned_get"] = req("GET", f"/api/v1/patients/{UNASSIGNED}", token=d_access)[0]
        out["doctor_clinical_summary"] = req(
            "GET",
            f"/api/v1/patients/{ASSIGNED}/clinical-summary",
            token=d_access,
        )[0]

    _, _, a1 = login(DOCTOR_EMAIL, DOCTOR_PASSWORD)
    _, _, b1 = login(DOCTOR_EMAIL, DOCTOR_PASSWORD)
    out["refresh_login_a"] = 200 if a1 else "fail"
    out["refresh_login_b"] = 200 if b1 else "fail"
    if a1 and b1:
        out["A_after_B_login_first_refresh"] = refresh_token(a1)[0]
        out["B_after_A_refresh"] = refresh_token(b1)[0]
        out["A_replay_old"] = refresh_token(a1)[0]
        out["B_replay_old"] = refresh_token(b1)[0]

    ll, l_access, l1 = login(DOCTOR_EMAIL, DOCTOR_PASSWORD)
    out["logout_precheck_login"] = ll
    if l1 and l_access:
        out["logout_status"] = req(
            "POST",
            "/api/v1/auth/logout",
            token=l_access,
            body={"refresh_token": l1},
        )[0]
        out["logout_refresh_replay"] = refresh_token(l1)[0]
    else:
        out["logout_test"] = "SKIP_login_failed"

    al, a_access, _ = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    out["admin_login"] = al
    if a_access:
        st, _, raw = req("GET", "/api/v1/auth/me", token=a_access)
        out["admin_me"] = st
        if st == 200:
            out["admin_role"] = json.loads(raw).get("role")

        st_default, _, raw_default = req("GET", "/api/v1/patients", token=a_access)
        out["admin_patients_list_default"] = st_default
        default_ids, admin_total = (
            _ids_from_list_body(raw_default) if st_default == 200 else (set(), None)
        )
        out["admin_list_total"] = admin_total
        out["admin_policy_on_default_page1"] = ASSIGNED in default_ids
        out["admin_unassigned_on_default_page1"] = UNASSIGNED in default_ids

        st_wide, _, raw_wide = req(
            "GET",
            f"/api/v1/patients?page=1&page_size={ADMIN_LIST_WIDE_PAGE_SIZE}",
            token=a_access,
        )
        out["admin_patients_list_wide"] = st_wide
        wide_ids, _ = _ids_from_list_body(raw_wide) if st_wide == 200 else (set(), None)
        out["admin_sees_assigned_in_wide_list"] = ASSIGNED in wide_ids
        out["admin_sees_unassigned_in_wide_list"] = UNASSIGNED in wide_ids
        out["admin_sees_assigned"] = ASSIGNED in wide_ids
        out["admin_sees_unassigned"] = UNASSIGNED in wide_ids

        out["admin_membership"] = req("GET", "/api/v1/organizations/me/membership", token=a_access)[0]
        out["admin_doctors_list"] = req(
            "GET",
            "/api/v1/organizations/me/members/doctors",
            token=a_access,
        )[0]
        out["admin_assigned_get"] = req("GET", f"/api/v1/patients/{ASSIGNED}", token=a_access)[0]
        out["admin_unassigned_get"] = req("GET", f"/api/v1/patients/{UNASSIGNED}", token=a_access)[0]
        out["admin_fixture_rbac_ok"] = (
            out["admin_assigned_get"] == 200 and out["admin_unassigned_get"] == 200
        )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
