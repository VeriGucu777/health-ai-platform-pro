"""One-off migration: wire API tests to org_assigned_patient_harness (test-only)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "tests" / "api"

CRUD_FILES = [
    "test_health_measurements.py",
    "test_medical_records.py",
    "test_appointments.py",
    "test_health_measurement_analytics.py",
    "test_health_measurement_insights.py",
    "test_diabetes_risk_assessment.py",
]

HARNESS_IMPORT = """from tests.support.org_assigned_patient_harness import (
    PATIENT_PAYLOAD,
    create_assigned_patient_for_doctor_headers as _create_patient,
    register_and_login_doctor as _register_and_login,
)
"""

CREATE_PATIENT_BLOCK = re.compile(
    r"\nasync def _create_patient\(client: AsyncClient, headers: dict\[str, str\]\) -> str:\n"
    r"    response = await client\.post\(\"/api/v1/patients\", json=PATIENT_PAYLOAD, headers=headers\)\n"
    r"    assert response\.status_code == 201\n"
    r"    return response\.json\(\)\[\"id\"\]\n",
    re.MULTILINE,
)

REGISTER_BLOCK = re.compile(
    r"\nasync def _register_and_login\(\n"
    r"    client: AsyncClient,\n"
    r"    \*,\n"
    r"    email: str,\n"
    r"    password: str = \"securepass123\",\n"
    r"    first_name: str = \"Test\",\n"
    r"    last_name: str = \"User\",\n"
    r"\) -> dict\[str, str\]:\n"
    r"    register_response = await client\.post\(\n"
    r"        \"/api/v1/auth/register\",\n"
    r"        json=\{\n"
    r"            \"email\": email,\n"
    r"            \"password\": password,\n"
    r"            \"first_name\": first_name,\n"
    r"            \"last_name\": last_name,\n"
    r"            \"role\": \"doctor\",\n"
    r"        \},\n"
    r"    \)\n"
    r"    assert register_response\.status_code == 201\n\n"
    r"    login_response = await client\.post\(\n"
    r"        \"/api/v1/auth/login\",\n"
    r"        json=\{\"email\": email, \"password\": password\},\n"
    r"    \)\n"
    r"    assert login_response\.status_code == 200\n"
    r"    token = login_response\.json\(\)\[\"access_token\"\]\n"
    r"    return \{\"Authorization\": f\"Bearer \{token\}\"\}\n",
    re.MULTILINE,
)

DIABETES_CREATE = re.compile(
    r"\nasync def _create_patient\(client: AsyncClient, headers: dict\[str, str\]\) -> str:\n"
    r"    response = await client\.post\(\"/api/v1/patients\", json=PATIENT_PAYLOAD, headers=headers\)\n"
    r"    assert response\.status_code == 201\n"
    r"    return response\.json\(\)\[\"id\"\]\n",
    re.MULTILINE,
)

DIABETES_REGISTER = re.compile(
    r"\nasync def _register_and_login\(client: AsyncClient, \*, email: str\) -> dict\[str, str\]:\n"
    r"    await client\.post\(\n"
    r"        \"/api/v1/auth/register\",\n"
    r"        json=\{\n"
    r"            \"email\": email,\n"
    r"            \"password\": \"securepass123\",\n"
    r"            \"first_name\": \"Test\",\n"
    r"            \"last_name\": \"User\",\n"
    r"            \"role\": \"doctor\",\n"
    r"        \},\n"
    r"    \)\n"
    r"    login_response = await client\.post\(\n"
    r"        \"/api/v1/auth/login\",\n"
    r"        json=\{\"email\": email, \"password\": \"securepass123\"\},\n"
    r"    \)\n"
    r"    token = login_response\.json\(\)\[\"access_token\"\]\n"
    r"    return \{\"Authorization\": f\"Bearer \{token\}\"\}\n",
    re.MULTILINE,
)


def ensure_harness_import(text: str) -> str:
    if "org_assigned_patient_harness" in text:
        return text
    if "PATIENT_PAYLOAD = {" in text:
        text = re.sub(
            r"PATIENT_PAYLOAD = \{[^}]+\}\n\n",
            "",
            text,
            count=1,
        )
    anchor = "from httpx import AsyncClient\n"
    if anchor not in text:
        raise ValueError("missing httpx import")
    return text.replace(anchor, anchor + "\n" + HARNESS_IMPORT + "\n", 1)


def add_fixtures(text: str) -> str:
    text = re.sub(
        r"\(client: AsyncClient\) -> None:",
        "(client: AsyncClient, user_repository, membership_repository,) -> None:",
        text,
    )
    text = re.sub(
        r"\(client: AsyncClient,\n    invalid_locale: str,\n\) -> None:",
        "(client: AsyncClient, user_repository, membership_repository, invalid_locale: str,) -> None:",
        text,
    )
    return text


def migrate_crud_file(name: str) -> None:
    path = API / name
    text = path.read_text(encoding="utf-8")
    if name == "test_diabetes_risk_assessment.py":
        text = DIABETES_CREATE.sub("\n", text)
        text = DIABETES_REGISTER.sub("\n", text)
    else:
        text = CREATE_PATIENT_BLOCK.sub("\n", text)
        text = REGISTER_BLOCK.sub("\n", text)
    text = ensure_harness_import(text)
    text = add_fixtures(text)
    path.write_text(text, encoding="utf-8")
    print(f"migrated {name}")


def main() -> None:
    for name in CRUD_FILES:
        migrate_crud_file(name)


if __name__ == "__main__":
    main()
