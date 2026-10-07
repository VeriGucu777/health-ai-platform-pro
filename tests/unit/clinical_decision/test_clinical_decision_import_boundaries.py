"""Ensure clinical decision foundation has no forbidden infrastructure imports."""

from __future__ import annotations

import ast
from pathlib import Path

_FORBIDDEN_ROOTS = frozenset(
    {
        "fastapi",
        "sqlalchemy",
        "httpx",
        "requests",
        "openai",
        "app.infrastructure.embeddings",
        "app.application.services.clinical_narrative_service",
        "app.application.services.clinical_retrieval_service",
    }
)

_SCAN_ROOTS = (
    Path("app/domain/clinical_decision"),
    Path("app/application/clinical_decision"),
)


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_clinical_decision_modules_avoid_forbidden_dependencies() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    violations: list[str] = []
    for rel in _SCAN_ROOTS:
        root = repo_root / rel
        for path in root.rglob("*.py"):
            for module in _imports_in_file(path):
                for forbidden in _FORBIDDEN_ROOTS:
                    if module == forbidden or module.startswith(forbidden + "."):
                        violations.append(f"{path.relative_to(repo_root)} imports {module}")
    assert violations == []
