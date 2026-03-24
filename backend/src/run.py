"""Run the filter pipeline against houses in input_data/.

Orchestrates: load houses → run filters → save results.
Skips houses that already have status >= FILTERED (resumable).
If criteria config changed since the last run, invalidates and re-runs.
"""

from __future__ import annotations

import logging

from src.config import load_criteria
from src.core import create_storage
from src.filters.text_filter import TextFilter
from src.models.house import HouseStatus
from src.runners.run_pipeline import FilterPipeline

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

# Ordered pipeline stages for resume comparison
_STATUS_ORDER = list(HouseStatus)


def _status_at_least(current: HouseStatus, minimum: HouseStatus) -> bool:
    return _STATUS_ORDER.index(current) >= _STATUS_ORDER.index(minimum)


def main() -> None:
    criteria = load_criteria()
    storage = create_storage()

    all_houses = storage.load_houses(criteria)
    if not all_houses:
        print("No houses found in input_data/houses/")
        return

    # Split: skip already-filtered houses, only process RAW ones
    to_process = [h for h in all_houses if not _status_at_least(h.status, HouseStatus.FILTERED)]
    already_done = [h for h in all_houses if _status_at_least(h.status, HouseStatus.FILTERED)]

    if already_done:
        print(f"Resuming: {len(already_done)} house(s) already filtered, skipping")

    if not to_process:
        print("All houses already filtered. Nothing to do.")
        return

    print(f"Processing {len(to_process)} house(s), criteria: {criteria}")

    pipeline = FilterPipeline()
    pipeline.add_filter(TextFilter())

    results = pipeline.run(to_process, criteria)

    storage.save_filter_results(results)

    print(f"\nResults: {len(results)}/{len(to_process)} passed")
    for h in results:
        print(f"  ✓ {h.slug} (status={h.status.value})")


if __name__ == "__main__":
    main()
