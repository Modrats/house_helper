"""Run the full filter pipeline against houses in input_data/.

Four stages, each resumable based on HouseStatus:

  Stage 1 — Text filter         (RAW        → FILTERED)
  Stage 2 — Room classification  (FILTERED   → CLASSIFIED)
  Stage 3 — Room + distance      (CLASSIFIED → EVALUATED)
  Stage 4 — Imagineering         (EVALUATED  → IMAGINEERED)  [opt-in: --imagineering]

Re-running is safe: each stage skips houses that have already advanced
past its target status.  Set AZURE_MAPS_KEY to enable the distance
filter; omitting it skips distance checks with a warning.

Imagineering calls the FLUX.2-pro API and costs money per image.
It is DISABLED by default.  Pass --imagineering to enable it.
"""

from __future__ import annotations

import argparse
import logging
import os

from src.config import ConfigLoader
from src.core import (
    create_imagineering_service,
    create_photo_checker,
    create_repository,
    create_room_classifier,
)
from src.filters.distance_filter import DistanceFilter
from src.filters.photo_criteria_filter import PhotoCriteriaFilter
from src.filters.room_filter import RoomTypeFilter
from src.filters.text_filter import TextFilter
from src.models.house import House, HouseStatus
from src.runners.run_pipeline import FilterPipeline

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logger = logging.getLogger(__name__)


def _print_stage_summary(label: str, passed: list[House], total: int) -> None:
    print(f"  {len(passed)}/{total} passed")
    for h in passed:
        print(f"    ✓ {h.slug}")


def main() -> None:
    parser = argparse.ArgumentParser(description="House Helper pipeline")
    parser.add_argument(
        "--imagineering",
        action="store_true",
        default=False,
        help="Run the imagineering stage (calls FLUX.2-pro — costs money per image).",
    )
    args = parser.parse_args()

    config = ConfigLoader()
    criteria = config.criteria()
    _, output_dir = config.storage_paths()
    repo = create_repository()

    # -----------------------------------------------------------------------
    # Stage 1 — Text filter  (RAW → FILTERED)
    # -----------------------------------------------------------------------
    all_houses = repo.load_houses(criteria)
    if not all_houses:
        print("No houses found in input_data/houses/")
        return

    raw = [h for h in all_houses if h.status == HouseStatus.RAW]
    if raw:
        print(f"\n── Stage 1: Text filter ({len(raw)} house(s)) ──")
        pipeline = FilterPipeline()
        pipeline.add_filter(TextFilter())
        passed = pipeline.run(raw, criteria)
        repo.save_filter_results(passed, criteria)
        _print_stage_summary("Text filter", passed, len(raw))
    else:
        skipped = sum(1 for h in all_houses if h.status != HouseStatus.RAW)
        print(f"\n── Stage 1: Text filter — skipped ({skipped} already processed) ──")

    # -----------------------------------------------------------------------
    # Stage 2 — Room classification  (FILTERED → CLASSIFIED)
    # -----------------------------------------------------------------------
    all_houses = repo.load_houses(criteria)
    to_classify = [h for h in all_houses if h.status == HouseStatus.FILTERED]
    if to_classify:
        print(f"\n── Stage 2: Room classification ({len(to_classify)} house(s)) ──")
        classifier = create_room_classifier()
        for h in to_classify:
            logger.info("Classifying photos for '%s'…", h.slug)
            classifier.classify_house(h.slug)
        classified = [h.with_status(HouseStatus.CLASSIFIED) for h in to_classify]
        repo.save_filter_results(classified, criteria)
        print(f"  {len(classified)}/{len(to_classify)} classified")
        for h in classified:
            print(f"    ✓ {h.slug}")
    else:
        skipped = sum(
            1 for h in all_houses if h.status not in (HouseStatus.RAW, HouseStatus.FILTERED)
        )
        print(f"\n── Stage 2: Room classification — skipped ({skipped} already processed) ──")

    # -----------------------------------------------------------------------
    # Stage 3 — Room type + distance filter  (CLASSIFIED → EVALUATED)
    # -----------------------------------------------------------------------
    all_houses = repo.load_houses(criteria)
    to_evaluate = [h for h in all_houses if h.status == HouseStatus.CLASSIFIED]
    if to_evaluate:
        print(f"\n── Stage 3: Evaluation filter ({len(to_evaluate)} house(s)) ──")
        pipeline = FilterPipeline()
        pipeline.add_filter(RoomTypeFilter(output_dir))
        pipeline.add_filter(PhotoCriteriaFilter(create_photo_checker()))

        azure_maps_key = os.environ.get("AZURE_MAPS_KEY")
        if azure_maps_key:
            pipeline.add_filter(DistanceFilter(azure_maps_key))
        else:
            logger.warning("AZURE_MAPS_KEY not set — distance filter skipped")

        evaluated = pipeline.run(to_evaluate, criteria)
        # Override status: FilterPipeline sets FILTERED, we want EVALUATED
        evaluated = [h.with_status(HouseStatus.EVALUATED) for h in evaluated]
        repo.save_filter_results(evaluated, criteria)
        _print_stage_summary("Evaluation filter", evaluated, len(to_evaluate))
    else:
        skipped = sum(1 for h in all_houses if h.status == HouseStatus.EVALUATED)
        print(f"\n── Stage 3: Evaluation filter — skipped ({skipped} already evaluated) ──")

    # -----------------------------------------------------------------------
    # Stage 4 — Imagineering  (EVALUATED → IMAGINEERED)  [opt-in]
    # -----------------------------------------------------------------------
    if not args.imagineering:
        print("\n── Stage 4: Imagineering — skipped (pass --imagineering to enable) ──")
    else:
        all_houses = repo.load_houses(criteria)
        to_imagineer = [h for h in all_houses if h.status == HouseStatus.EVALUATED]
        if to_imagineer:
            print(f"\n── Stage 4: Imagineering ({len(to_imagineer)} house(s)) ──")
            service = create_imagineering_service()
            for h in to_imagineer:
                logger.info("Imagineering '%s'…", h.slug)
                service.imagineer_house(h.slug)
            imagineered = [h.with_status(HouseStatus.IMAGINEERED) for h in to_imagineer]
            repo.save_filter_results(imagineered, criteria)
            print(f"  {len(imagineered)}/{len(to_imagineer)} imagineered")
            for h in imagineered:
                print(f"    ✓ {h.slug}")
        else:
            skipped = sum(1 for h in all_houses if h.status == HouseStatus.IMAGINEERED)
            print(f"\n── Stage 4: Imagineering — skipped ({skipped} already imagineered) ──")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    all_houses = repo.load_houses(criteria)
    by_status: dict[str, int] = {}
    for h in all_houses:
        by_status[h.status.value] = by_status.get(h.status.value, 0) + 1
    print("\n── Pipeline complete ──")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
