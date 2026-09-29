import re
from pathlib import Path

pat = re.compile(
    r"(\s*)owner_headers = await _register_and_login\(client, email=\"([^\"]+)\"\)\n"
    r"\s*other_headers = await _register_and_login\(client, email=\"([^\"]+)\"\)\n"
    r"(\s*\n)?"
    r"\s*patient_id = await _create_patient\(client, owner_headers\)",
    re.MULTILINE,
)


def repl(match: re.Match[str]) -> str:
    ind = match.group(1)
    e1, e2 = match.group(2), match.group(3)
    blank = match.group(4) or "\n"
    return (
        f"{ind}owner_email = \"{e1}\"\n"
        f"{ind}other_email = \"{e2}\"\n"
        f"{ind}owner_headers = await _register_and_login(client, email=owner_email)\n"
        f"{ind}other_headers = await _register_and_login(client, email=other_email)\n"
        f"{blank}"
        f"{ind}patient_id = await _create_patient(\n"
        f"{ind}    client,\n"
        f"{ind}    user_repository,\n"
        f"{ind}    membership_repository,\n"
        f"{ind}    owner_headers,\n"
        f"{ind}    extra_org_doctor_emails=(other_email,),\n"
        f"{ind})"
    )


for path in Path("tests/api").glob("*.py"):
    text = path.read_text(encoding="utf-8")
    updated = pat.sub(repl, text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        print("owner fix", path.name)
