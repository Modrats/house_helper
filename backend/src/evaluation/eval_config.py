"""Load evaluation thresholds from config/eval_thresholds.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "eval_thresholds.yaml"


@lru_cache(maxsize=1)
def _load_all() -> dict:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def load_thresholds(stage: str) -> dict[str, float]:
    """Return the threshold dict for *stage* (e.g. ``'text_filter'``)."""
    return dict(_load_all()[stage])
