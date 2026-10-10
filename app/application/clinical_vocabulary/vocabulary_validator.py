"""Validate controlled vocabulary manifests under clinical_knowledge/vocabularies/."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from app.application.clinical_vocabulary.exceptions import ClinicalVocabularyLoadError
from app.domain.clinical_vocabulary.enums import (
    VocabularyCategory,
    VocabularyClinicalReviewStatus,
    VocabularyItemStatus,
)
from app.domain.clinical_vocabulary.models import ControlledVocabularyManifest
from app.infrastructure.clinical_vocabulary.filesystem_registry import load_vocabulary_manifests_from_root
from app.infrastructure.clinical_knowledge.yaml_loader import load_yaml_mapping

_KEY_PATTERN = re.compile(
    r"^card\.(complaint|finding|question|answer_code|vital|unit|onset)\.[a-z][a-z0-9_]*$",
)
_CATEGORY_FROM_KEY = {
    "complaint": VocabularyCategory.COMPLAINT,
    "finding": VocabularyCategory.FINDING,
    "question": VocabularyCategory.QUESTION,
    "answer_code": VocabularyCategory.ANSWER_CODE,
    "vital": VocabularyCategory.VITAL,
    "unit": VocabularyCategory.UNIT,
    "onset": VocabularyCategory.ONSET,
}


@dataclass
class VocabularyValidationIssue:
    code: str
    message: str
    path: str | None = None


@dataclass
class VocabularyValidationResult:
    issues: list[VocabularyValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _schema_validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _detect_replacement_cycle(keys: dict[str, str | None]) -> bool:
    for start in keys:
        visited: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in visited:
                return True
            visited.add(current)
            current = keys.get(current)
    return False


class DefaultVocabularyValidator:
    def validate_catalog(self, knowledge_root: Path) -> VocabularyValidationResult:
        result = VocabularyValidationResult()
        root = knowledge_root.resolve()
        schema_path = root / "schemas" / "controlled_vocabulary_manifest.schema.json"
        if not schema_path.is_file():
            result.issues.append(
                VocabularyValidationIssue(
                    code="missing_schema",
                    message=f"missing schema: {schema_path}",
                    path=str(schema_path),
                ),
            )
            return result

        validator = _schema_validator(schema_path)
        vocab_dir = root / "vocabularies"
        if not vocab_dir.is_dir():
            return result

        manifests: tuple[ControlledVocabularyManifest, ...] = ()
        try:
            manifests = load_vocabulary_manifests_from_root(root)
        except ClinicalVocabularyLoadError as exc:
            result.issues.append(
                VocabularyValidationIssue(code="vocabulary_load_failed", message=str(exc)),
            )
            return result

        from app.infrastructure.clinical_knowledge.yaml_loader import iter_manifest_yaml_files_recursive

        for path in iter_manifest_yaml_files_recursive(vocab_dir):
            rel = str(path.relative_to(root))
            try:
                data = load_yaml_mapping(path, knowledge_root=root)
            except ValueError as exc:
                result.issues.append(
                    VocabularyValidationIssue(code="yaml_invalid", message=str(exc), path=rel),
                )
                continue
            for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
                result.issues.append(
                    VocabularyValidationIssue(
                        code="schema_violation",
                        message=error.message,
                        path=f"{rel}#{'/'.join(str(p) for p in error.path)}",
                    ),
                )

        for manifest in manifests:
            self._validate_manifest_semantics(manifest, result)

        return result

    def _validate_manifest_semantics(
        self,
        manifest: ControlledVocabularyManifest,
        result: VocabularyValidationResult,
    ) -> None:
        prefix = f"{manifest.vocabulary_id}@{manifest.vocabulary_version}"
        keys_seen: set[str] = set()
        replacement_map: dict[str, str | None] = {}

        for term in manifest.terms:
            if term.key in keys_seen:
                result.issues.append(
                    VocabularyValidationIssue(
                        code="duplicate_key",
                        message=f"duplicate vocabulary key {term.key!r}",
                        path=prefix,
                    ),
                )
            keys_seen.add(term.key)
            replacement_map[term.key] = term.replacement_key

            if not _KEY_PATTERN.match(term.key):
                result.issues.append(
                    VocabularyValidationIssue(
                        code="invalid_key_pattern",
                        message=f"invalid key pattern: {term.key!r}",
                        path=prefix,
                    ),
                )

            segment = term.key.split(".")[1] if term.key.count(".") >= 2 else ""
            expected = _CATEGORY_FROM_KEY.get(segment)
            if expected is not None and term.category != expected:
                result.issues.append(
                    VocabularyValidationIssue(
                        code="category_key_mismatch",
                        message=f"key {term.key!r} category {term.category.value} mismatch",
                        path=prefix,
                    ),
                )

            if term.status == VocabularyItemStatus.DEPRECATED and not term.replacement_key:
                result.issues.append(
                    VocabularyValidationIssue(
                        code="deprecated_without_replacement",
                        message=f"deprecated term {term.key!r} missing replacement_key",
                        path=prefix,
                    ),
                )

            if term.status == VocabularyItemStatus.APPROVED_PROD:
                if term.clinical_review_status != VocabularyClinicalReviewStatus.CLINICALLY_APPROVED:
                    result.issues.append(
                        VocabularyValidationIssue(
                            code="prod_without_clinical_approval",
                            message=f"approved_prod term {term.key!r} lacks clinically_approved review",
                            path=prefix,
                        ),
                    )

            for answer_code in term.allowed_answer_codes:
                if not answer_code.startswith("card.answer_code."):
                    result.issues.append(
                        VocabularyValidationIssue(
                            code="invalid_answer_code_ref",
                            message=f"invalid allowed_answer_code on {term.key!r}",
                            path=prefix,
                        ),
                    )

            if term.default_unit_key and not term.default_unit_key.startswith("card.unit."):
                result.issues.append(
                    VocabularyValidationIssue(
                        code="invalid_unit_ref",
                        message=f"invalid default_unit_key on {term.key!r}",
                        path=prefix,
                    ),
                )

        key_index = {term.key: term for term in manifest.terms}
        for term in manifest.terms:
            if term.replacement_key and term.replacement_key not in key_index:
                result.issues.append(
                    VocabularyValidationIssue(
                        code="replacement_unresolved",
                        message=f"replacement_key {term.replacement_key!r} not found for {term.key!r}",
                        path=prefix,
                    ),
                )
            if term.default_unit_key and term.default_unit_key not in key_index:
                result.issues.append(
                    VocabularyValidationIssue(
                        code="unit_unresolved",
                        message=f"default_unit_key {term.default_unit_key!r} not found for {term.key!r}",
                        path=prefix,
                    ),
                )
            for answer_code in term.allowed_answer_codes:
                if answer_code not in key_index:
                    result.issues.append(
                        VocabularyValidationIssue(
                            code="answer_code_unresolved",
                            message=f"allowed_answer_code {answer_code!r} not found for {term.key!r}",
                            path=prefix,
                        ),
                    )

        if _detect_replacement_cycle(replacement_map):
            result.issues.append(
                VocabularyValidationIssue(
                    code="replacement_cycle",
                    message="replacement_key cycle detected",
                    path=prefix,
                ),
            )
