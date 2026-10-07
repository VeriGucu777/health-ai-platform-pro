#!/usr/bin/env python3
"""Validate the git-versioned clinical knowledge catalog (Phase 0B.1)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.application.clinical_knowledge.rule_catalog_validator import DefaultRuleCatalogValidator
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root


def main() -> int:
    root = repository_clinical_knowledge_root()
    result = DefaultRuleCatalogValidator().validate_catalog(root)
    if result.ok:
        print(f"Clinical knowledge catalog OK: {root}")
        return 0
    print(f"Clinical knowledge catalog INVALID: {root}", file=sys.stderr)
    for issue in result.issues:
        location = f" ({issue.path})" if issue.path else ""
        print(f"  [{issue.code}]{location} {issue.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
