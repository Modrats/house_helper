"""Load pipeline configuration from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "criteria.yaml"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_raw(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and return the raw YAML config."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_criteria(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load filter criteria from YAML config.

    The YAML structure maps filter names to their criteria dicts.
    The 'storage' section is excluded — only filter sections are merged.

    Returns:
        A flat dict merging all filter sections, keyed by criteria field name.
    """
    raw = _load_raw(path)

    criteria: dict[str, Any] = {}
    for key, section in raw.items():
        if key == "storage":
            continue
        if isinstance(section, dict):
            criteria.update(section)
    return criteria


def load_storage_paths(
    path: Path = DEFAULT_CONFIG_PATH,
) -> tuple[Path, Path]:
    """Load input and output directory paths from config.

    Paths in YAML are relative to the repo root.

    Returns:
        Tuple of (input_dir, output_dir) as absolute Paths.

    Raises:
        KeyError: If the storage section is missing from config.
    """
    raw = _load_raw(path)
    storage = raw["storage"]
    input_dir = REPO_ROOT / storage["input_dir"]
    output_dir = REPO_ROOT / storage["output_dir"]
    return input_dir, output_dir


def load_photo_criteria(
    path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, dict[str, list[str]]]:
    """Load photo criteria configuration keyed by room type.

    Each room type maps to ``{"required": [...], "preferred": [...]}``.

    Returns:
        Dict mapping room type strings to criteria dicts.

    Raises:
        KeyError: If the photo_criteria section is missing from config.
    """
    raw = _load_raw(path)
    return raw["photo_criteria"]
