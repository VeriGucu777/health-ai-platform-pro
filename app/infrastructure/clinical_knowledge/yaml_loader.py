"""Safe UTF-8 YAML loading for knowledge manifests."""

from pathlib import Path
from typing import Any

import yaml

from app.application.clinical_knowledge.exceptions import ClinicalKnowledgeCatalogIntegrityError


def ensure_manifest_path_under_root(path: Path, knowledge_root: Path) -> Path:
    """Resolve path and reject escapes outside the trusted knowledge root."""
    resolved = path.resolve()
    root = knowledge_root.resolve()
    if not resolved.is_relative_to(root):
        raise ClinicalKnowledgeCatalogIntegrityError(
            f"manifest path escapes clinical_knowledge root: {path}",
        )
    return resolved


def load_yaml_mapping(path: Path, *, knowledge_root: Path | None = None) -> dict[str, Any]:
    """Load one YAML file as a mapping using safe_load only."""
    if knowledge_root is not None:
        ensure_manifest_path_under_root(path, knowledge_root)
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in {path}: {exc}") from exc
    if data is None:
        raise ValueError(f"empty YAML document: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping at root of {path}, got {type(data).__name__}")
    return data


def iter_manifest_yaml_files(directory: Path) -> tuple[Path, ...]:
    """List *.yaml and *.yml files in deterministic sorted order (ignores README etc.)."""
    if not directory.is_dir():
        return ()
    paths = [*directory.glob("*.yaml"), *directory.glob("*.yml")]
    return tuple(sorted(paths, key=lambda p: str(p).replace("\\", "/").lower()))


def iter_manifest_yaml_files_recursive(directory: Path) -> tuple[Path, ...]:
    """List manifest YAML files recursively under rules/."""
    if not directory.is_dir():
        return ()
    paths = [*directory.rglob("*.yaml"), *directory.rglob("*.yml")]
    return tuple(sorted(paths, key=lambda p: str(p).replace("\\", "/").lower()))
