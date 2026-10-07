"""Safe UTF-8 YAML loading for knowledge manifests."""

from pathlib import Path
from typing import Any

import yaml


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load one YAML file as a mapping using safe_load only."""
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if data is None:
        raise ValueError(f"empty YAML document: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping at root of {path}, got {type(data).__name__}")
    return data


def iter_yaml_files(directory: Path) -> tuple[Path, ...]:
    """List *.yaml files in deterministic sorted order."""
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.yaml")))
