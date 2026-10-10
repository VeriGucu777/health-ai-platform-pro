#!/usr/bin/env python3
"""Validate git-versioned controlled vocabulary manifests (Phase 2A)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.application.clinical_vocabulary.vocabulary_validator import DefaultVocabularyValidator
from app.infrastructure.clinical_knowledge.paths import repository_clinical_knowledge_root


def main() -> int:
    root = repository_clinical_knowledge_root()
    result = DefaultVocabularyValidator().validate_catalog(root)
    if result.ok:
        print(f"Controlled vocabulary catalog OK: {root / 'vocabularies'}")
        return 0
    print(f"Controlled vocabulary catalog INVALID: {root}", file=sys.stderr)
    for issue in result.issues:
        location = f" ({issue.path})" if issue.path else ""
        print(f"  [{issue.code}]{location} {issue.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
