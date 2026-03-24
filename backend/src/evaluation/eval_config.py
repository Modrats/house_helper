"""Load evaluation thresholds from src/evaluation/config/eval_thresholds.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


def _get_config_path() -> Path:
    """Return the path to the eval_thresholds.yaml config file.

    Extracted as a function so tests can monkeypatch it
    (``monkeypatch.setattr("src.evaluation.eval_config._get_config_path", ...)``)
    without touching the module-level constant.
    """
    return Path(__file__).parent / "config" / "eval_thresholds.yaml"


@lru_cache(maxsize=1)
def _load_all() -> dict:
    """Load and cache the YAML config file.

    The cache means the file is read once per process.
    In tests that need a fresh load, call ``_load_all.cache_clear()`` before
    the test and restore it afterwards.
    """
    with _get_config_path().open() as f:
        return yaml.safe_load(f)


def load_thresholds(stage: str) -> dict[str, float]:
    """Return the threshold dict for *stage* (e.g. ``'text_filter'``)."""
    return dict(_load_all()[stage])
