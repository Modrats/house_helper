"""Load pipeline configuration from a YAML file or cloud source."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_YAML = Path(__file__).resolve().parent.parent / "config" / "criteria.yaml"


class ConfigLoader:
    """Loads pipeline configuration from a YAML file.

    Instantiate once and call the accessor methods.  To swap in a cloud-backed
    source (e.g. Azure App Configuration), subclass or replace this with a
    compatible implementation that exposes the same methods.

    Args:
        path: Path to the YAML config file.  Defaults to the bundled
            ``config/criteria.yaml`` relative to this source tree.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_YAML
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is None:
            with open(self._path) as fh:
                self._data = yaml.safe_load(fh)
        return self._data

    def criteria(self) -> dict[str, Any]:
        """Return merged filter criteria (all non-storage YAML sections)."""
        raw = self._load()
        result: dict[str, Any] = {}
        for key, section in raw.items():
            if key != "storage" and isinstance(section, dict):
                result.update(section)
        return result

    def storage_paths(self) -> tuple[Path, Path]:
        """Return (input_dir, output_dir) as absolute Paths."""
        storage = self._load()["storage"]
        return (
            _REPO_ROOT / storage["input_dir"],
            _REPO_ROOT / storage["output_dir"],
        )

    def distance_config(self) -> list[dict[str, str | list[str]]]:
        """Return the list of distance destinations."""
        return self._load()["distance"]["destinations"]

    def photo_criteria(self) -> dict[str, dict[str, list[str]]]:
        """Return photo criteria keyed by room type."""
        return self._load()["photo_criteria"]
