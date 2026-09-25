#!/usr/bin/env python3
"""Analyze/repair/verify demo-live-policy assignment fixtures via HTTP API (ops only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.application.seeding.demo_clinic_admin_seed import (  # noqa: E402
    DEMO_CLINIC_ADMIN_EMAIL,
    DEMO_ORGANIZATION_NAME,
)
from app.application.seeding.demo_organization_fixture_seed import (  # noqa: E402
    DEMO_DOCTOR_EMAIL,
    DEMO_PATIENT_DATE_OF_BIRTH,
    DEMO_PATIENT_FIRST_NAME,
    DEMO_PATIENT_LAST_NAME,
    DEMO_PATIENT_SEED_MARKER,
)
from app.application.seeding.demo_unassigned_patient_fixture_seed import (  # noqa: E402
    DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH,
    DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
    DEMO_UNASSIGNED_PATIENT_LAST_NAME,
    DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
)

BASE = os.getenv("PRODUCTION_API_BASE", "https://health-ai-platform-pro.onrender.com").rstrip("/")
API = BASE + "/api/v1"
RANGE_Q = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"

ADMIN_EMAIL = os.getenv("DEMO_CLINIC_ADMIN_EMAIL", DEMO_CLINIC_ADMIN_EMAIL)
DOCTOR_EMAIL = os.getenv("DEMO_DOCTOR_EMAIL", DEMO_DOCTOR_EMAIL)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        msg = f"{name} must be set in the environment (not committed)."
        raise SystemExit(msg)
    return value


def _req(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
) -> tuple[int, Any]:
    url = API + path
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read()
            if raw[:4] == b"%PDF":
                return resp.status, {"pdf": True, "bytes": len(raw)}
            if raw:
                return resp.status, json.loads(raw.decode())
            return resp.status, None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw.decode()) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode(errors="replace")[:200]
        return exc.code, payload


def _login(email: str, password: str) -> str:
    status, data = _req("POST", "/auth/login", body={"email": email, "password": password})
    if status != 200 or not isinstance(data, dict):
        raise SystemExit(f"login failed status={status}")
    token = data.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise SystemExit("login failed: access token missing")
    return token


def _assert_demo_organization(membership: dict[str, Any] | None) -> None:
    if not isinstance(membership, dict):
        raise SystemExit("demo organization membership check failed: no membership payload")
    org_name = membership.get("organization_name")
    if org_name != DEMO_ORGANIZATION_NAME:
        raise SystemExit(
            "refusing to continue: organization_name does not match demo-live-policy fixture "
            f"(expected {DEMO_ORGANIZATION_NAME!r}, got {org_name!r})",
        )


def _date_matches(row_dob: Any, expected_iso: str) -> bool:
    if row_dob is None:
        return True
    text = str(row_dob)
    return text.startswith(expected_iso)


def _find_fixture_patient(
    items: list[dict],
    *,
    marker: str,
    first_name: str,
    last_name: str,
    date_of_birth_iso: str,
) -> dict | None:
    for row in items:
        notes = row.get("notes") or ""
        if marker in notes:
            return row
    for row in items:
        if row.get("first_name") != first_name or row.get("last_name") != last_name:
            continue
        if _date_matches(row.get("date_of_birth"), date_of_birth_iso):
            return row
    return None


def _doctor_assignment(items: list[dict], doctor_id: str) -> dict | None:
    for row in items:
        if row.get("assignee_user_id") == doctor_id:
            return row
    return None


def _count_list(token: str, path: str) -> int:
    status, data = _req("GET", path, token=token)
    if status != 200 or not isinstance(data, dict):
        return -1
    items = data.get("items")
    if isinstance(items, list):
        return len(items)
    return 0


def _resolve_fixture_patients(items: list[dict]) -> tuple[dict, dict]:
    policy = _find_fixture_patient(
        items,
        marker=DEMO_PATIENT_SEED_MARKER,
        first_name=DEMO_PATIENT_FIRST_NAME,
        last_name=DEMO_PATIENT_LAST_NAME,
        date_of_birth_iso=DEMO_PATIENT_DATE_OF_BIRTH.isoformat(),
    )
    unassigned = _find_fixture_patient(
        items,
        marker=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
        first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
        last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
        date_of_birth_iso=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH.isoformat(),
    )
    if policy is None or unassigned is None:
        raise SystemExit(
            "demo policy or unassigned fixture patient not found "
            "(seed marker / name / DOB mismatch)",
        )
    return policy, unassigned


def analyze(admin_token: str, doctor_id: str) -> dict[str, Any]:
    _, membership = _req("GET", "/organizations/me/membership", admin_token)
    _assert_demo_organization(membership if isinstance(membership, dict) else None)

    _, doctors = _req("GET", "/organizations/me/members/doctors", admin_token)
    _, listed = _req("GET", "/patients?page=1&page_size=100", admin_token)
    items = listed.get("items", []) if isinstance(listed, dict) else []

    policy, unassigned = _resolve_fixture_patients(items)
    pilots = [p for p in items if p.get("first_name") == "Demo" and p.get("last_name") == "Pilot Patient"]

    report: dict[str, Any] = {
        "organization": membership.get("organization_name") if isinstance(membership, dict) else None,
        "doctor_membership_active": any(
            d.get("email") == DOCTOR_EMAIL for d in (doctors.get("items", []) if isinstance(doctors, dict) else [])
        ),
        "duplicate_demo_pilot_patient_count": len(pilots),
        "policy_patient": None,
        "unassigned_patient": None,
        "pilot_inventory": [],
    }

    for label, patient in (("policy", policy), ("unassigned", unassigned)):
        pid = patient["id"]
        _, assignments = _req("GET", f"/patients/{pid}/assignments", admin_token)
        assign_items = assignments.get("items", []) if isinstance(assignments, dict) else []
        doc_row = _doctor_assignment(assign_items, doctor_id)
        report[f"{label}_patient"] = {
            "id_prefix": pid[:8],
            "created_at": patient.get("created_at"),
            "has_seed_marker": bool(
                (patient.get("notes") or "").find(
                    DEMO_PATIENT_SEED_MARKER if label == "policy" else DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
                )
                >= 0,
            ),
            "doctor_assignment_status": doc_row.get("status") if doc_row else None,
            "doctor_assignment_id_prefix": (doc_row.get("id") or "")[:8] if doc_row else None,
            "assignments_total": len(assign_items),
        }

    for pilot in pilots[:25]:
        pid = pilot["id"]
        _, assignments = _req("GET", f"/patients/{pid}/assignments", admin_token)
        a_items = assignments.get("items", []) if isinstance(assignments, dict) else []
        _, consents = _req("GET", f"/patients/{pid}/consents", admin_token)
        c_items = consents.get("items", []) if isinstance(consents, dict) else []
        inv = {
            "id": pid,
            "created_at": pilot.get("created_at"),
            "assignments_count": len(a_items),
            "consents_count": len(c_items),
            "medical_records_count": _count_list(
                admin_token,
                f"/medical-records?patient_id={urllib.parse.quote(pid)}",
            ),
            "measurements_count": _count_list(
                admin_token,
                f"/health-measurements?patient_id={urllib.parse.quote(pid)}",
            ),
            "appointments_count": _count_list(
                admin_token,
                f"/appointments?patient_id={urllib.parse.quote(pid)}",
            ),
        }
        _, risk = _req(
            "GET",
            f"/patients/{pid}/risk-assessments/history?{RANGE_Q}",
            admin_token,
        )
        if isinstance(risk, dict) and isinstance(risk.get("items"), list):
            inv["risk_history_count"] = len(risk["items"])
        else:
            inv["risk_history_count"] = 0 if isinstance(risk, dict) else -1
        report["pilot_inventory"].append(inv)

    return report


def repair(
    admin_token: str,
    doctor_id: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    _, membership = _req("GET", "/organizations/me/membership", admin_token)
    _assert_demo_organization(membership if isinstance(membership, dict) else None)

    _, listed = _req("GET", "/patients?page=1&page_size=100", admin_token)
    items = listed.get("items", []) if isinstance(listed, dict) else []
    policy, unassigned = _resolve_fixture_patients(items)

    policy_id = policy["id"]
    unassigned_id = unassigned["id"]

    _, policy_assignments = _req("GET", f"/patients/{policy_id}/assignments", admin_token)
    pa_items = policy_assignments.get("items", []) if isinstance(policy_assignments, dict) else []
    policy_before = _doctor_assignment(pa_items, doctor_id)

    _, unassigned_assignments = _req("GET", f"/patients/{unassigned_id}/assignments", admin_token)
    ua_items = unassigned_assignments.get("items", []) if isinstance(unassigned_assignments, dict) else []
    unassigned_before = _doctor_assignment(ua_items, doctor_id)

    plan: dict[str, Any] = {
        "dry_run": dry_run,
        "policy_assignment_before": policy_before.get("status") if policy_before else None,
        "unassigned_assignment_before": unassigned_before.get("status") if unassigned_before else None,
        "planned_policy_action": None,
        "planned_unassigned_action": None,
    }

    needs_policy_repair = policy_before is None or policy_before.get("status") != "active"
    needs_unassigned_deactivate = (
        unassigned_before is not None and unassigned_before.get("status") == "active"
    )

    if needs_policy_repair:
        plan["planned_policy_action"] = "activate_or_create_doctor_assignment"
    else:
        plan["planned_policy_action"] = "none"

    if needs_unassigned_deactivate:
        plan["planned_unassigned_action"] = "deactivate_doctor_assignment"
    else:
        plan["planned_unassigned_action"] = "none"

    if dry_run:
        plan["policy_assignment_after"] = "active" if not needs_policy_repair else "active (planned)"
        plan["unassigned_assignment_after"] = (
            "inactive (planned)"
            if needs_unassigned_deactivate
            else (unassigned_before.get("status") if unassigned_before else None)
        )
        return plan

    policy_after_status = None
    if needs_policy_repair:
        status, created = _req(
            "POST",
            f"/patients/{policy_id}/assignments",
            admin_token,
            {"assignee_user_id": doctor_id, "is_primary": True},
        )
        if status not in (200, 201):
            raise SystemExit(f"policy assignment repair failed status={status}")
        if isinstance(created, dict):
            policy_after_status = created.get("status")
        else:
            policy_after_status = "active"
    else:
        policy_after_status = "active"

    unassigned_after_status = unassigned_before.get("status") if unassigned_before else None
    if needs_unassigned_deactivate and unassigned_before is not None:
        aid = unassigned_before["id"]
        status, patched = _req("PATCH", f"/patients/{unassigned_id}/assignments/{aid}", admin_token)
        if status != 200:
            raise SystemExit(f"unassigned deactivation failed status={status}")
        if isinstance(patched, dict):
            unassigned_after_status = patched.get("status")

    plan["policy_assignment_after"] = policy_after_status
    plan["unassigned_assignment_after"] = unassigned_after_status
    return plan


def verify(doctor_token: str, admin_token: str, doctor_id: str) -> dict[str, Any]:
    _, membership = _req("GET", "/organizations/me/membership", admin_token)
    _assert_demo_organization(membership if isinstance(membership, dict) else None)

    _, listed_doc = _req("GET", "/patients?page=1&page_size=100", doctor_token)
    doc_items = listed_doc.get("items", []) if isinstance(listed_doc, dict) else []
    policy = _find_fixture_patient(
        doc_items,
        marker=DEMO_PATIENT_SEED_MARKER,
        first_name=DEMO_PATIENT_FIRST_NAME,
        last_name=DEMO_PATIENT_LAST_NAME,
        date_of_birth_iso=DEMO_PATIENT_DATE_OF_BIRTH.isoformat(),
    )
    unassigned_visible = (
        _find_fixture_patient(
            doc_items,
            marker=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
            first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
            last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
            date_of_birth_iso=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH.isoformat(),
        )
        is not None
    )

    _, listed_admin = _req("GET", "/patients?page=1&page_size=100", admin_token)
    admin_items = listed_admin.get("items", []) if isinstance(listed_admin, dict) else []
    admin_policy = _find_fixture_patient(
        admin_items,
        marker=DEMO_PATIENT_SEED_MARKER,
        first_name=DEMO_PATIENT_FIRST_NAME,
        last_name=DEMO_PATIENT_LAST_NAME,
        date_of_birth_iso=DEMO_PATIENT_DATE_OF_BIRTH.isoformat(),
    )
    admin_unassigned = _find_fixture_patient(
        admin_items,
        marker=DEMO_UNASSIGNED_PATIENT_SEED_MARKER,
        first_name=DEMO_UNASSIGNED_PATIENT_FIRST_NAME,
        last_name=DEMO_UNASSIGNED_PATIENT_LAST_NAME,
        date_of_birth_iso=DEMO_UNASSIGNED_PATIENT_DATE_OF_BIRTH.isoformat(),
    )

    out: dict[str, Any] = {
        "doctor_login": 200,
        "doctor_list_has_policy": policy is not None,
        "doctor_list_hides_unassigned": not unassigned_visible,
        "doctor_create_patient": _req(
            "POST",
            "/patients",
            doctor_token,
            {
                "first_name": "Should",
                "last_name": "Fail",
                "date_of_birth": "1990-01-01",
                "gender": "male",
            },
        )[0],
        "doctor_management_api": _req("GET", "/organizations/me/membership", doctor_token)[0],
        "admin_sees_policy": admin_policy is not None,
        "admin_sees_unassigned": admin_unassigned is not None,
    }

    if policy:
        pid = policy["id"]
        out["policy_get"] = _req("GET", f"/patients/{pid}", doctor_token)[0]
        out["policy_timeline"] = _req("GET", f"/patients/{pid}/clinical-timeline", doctor_token)[0]
        out["policy_pdf"] = _req(
            "GET",
            f"/patients/{pid}/reports/health-summary.pdf?{RANGE_Q}",
            doctor_token,
        )[0]
        out["policy_risk"] = _req(
            "GET",
            f"/patients/{pid}/risk-assessments/diabetes?{RANGE_Q}",
            doctor_token,
        )[0]

    if admin_unassigned:
        upid = admin_unassigned["id"]
        out["unassigned_get"] = _req("GET", f"/patients/{upid}", doctor_token)[0]
        out["unassigned_timeline"] = _req("GET", f"/patients/{upid}/clinical-timeline", doctor_token)[0]
        out["unassigned_pdf"] = _req(
            "GET",
            f"/patients/{upid}/reports/health-summary.pdf?{RANGE_Q}",
            doctor_token,
        )[0]
        out["unassigned_risk"] = _req(
            "GET",
            f"/patients/{upid}/risk-assessments/diabetes?{RANGE_Q}",
            doctor_token,
        )[0]

    sample = policy or admin_policy
    if sample:
        spid = sample["id"]
        out["admin_assignments"] = _req("GET", f"/patients/{spid}/assignments", admin_token)[0]
        out["admin_consents"] = _req("GET", f"/patients/{spid}/consents", admin_token)[0]

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demo live policy fixture ops (default: read-only analyze).",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="analyze",
        choices=("analyze", "repair", "verify"),
        help="analyze=read-only inventory (default); repair=mutate assignments; verify=RBAC checks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With repair: show planned assignment changes without writing.",
    )
    parser.add_argument(
        "--confirm-repair",
        action="store_true",
        help="Required for repair without --dry-run to mutate production assignments.",
    )
    args = parser.parse_args()

    if args.action == "repair" and not args.dry_run and not args.confirm_repair:
        print(
            "Refusing repair: pass --confirm-repair to mutate assignments, or --dry-run to preview.",
            file=sys.stderr,
        )
        return 1

    admin_password = _require_env("DEMO_CLINIC_ADMIN_PASSWORD")
    doctor_password = _require_env("DEMO_DOCTOR_PASSWORD")

    admin_token = _login(ADMIN_EMAIL, admin_password)
    doctor_token = _login(DOCTOR_EMAIL, doctor_password)
    _, me = _req("GET", "/auth/me", doctor_token)
    doctor_id = me.get("id") if isinstance(me, dict) else None
    if not doctor_id:
        raise SystemExit("doctor id missing")

    if args.action == "analyze":
        print(json.dumps({"analyze": analyze(admin_token, doctor_id)}, indent=2))
    elif args.action == "repair":
        print(
            json.dumps(
                {"repair": repair(admin_token, doctor_id, dry_run=args.dry_run)},
                indent=2,
            ),
        )
    elif args.action == "verify":
        print(json.dumps({"verify": verify(doctor_token, admin_token, doctor_id)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
