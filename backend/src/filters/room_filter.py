"""RoomTypeFilter — filters houses by room types detected by the room classifier.

Reads pre-computed classification results written by AzureOpenAIRoomClassifier
and checks them against room-type criteria.  Houses that have not yet been
classified pass through without penalty (empty FilterResult).

Criteria keys:
    p1_room_types: list[str] — room types that MUST be present (ALL required)
    p2_room_types: list[str] — nice-to-have room types (ANY must be present)
    excluded_room_types: list[str] — room types that disqualify the house
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..interfaces.filter import IFilter
from ..models.house import FilterResult, House
from ..observability import get_logger

logger = get_logger(__name__)


class RoomTypeFilter(IFilter):
    """Filters houses based on room types detected in classified photos.

    Reads ``room_classifications.json`` produced by the classifier stage.
    Houses with no classification file are passed through so the pipeline
    can still run if classification was skipped or failed for some houses.

    Args:
        output_dir: Root output directory (same value passed to the classifier).
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    @property
    def name(self) -> str:
        return "room_filter"

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        p1_types = criteria.get("p1_room_types", [])
        p2_types = criteria.get("p2_room_types", [])
        excluded_types = criteria.get("excluded_room_types", [])

        results: dict[str, FilterResult] = {}
        for house in houses:
            detected = self._load_detected_types(house.slug)
            if detected is None:
                logger.warning(
                    "No classification results for '%s' — room filter skipped", house.slug
                )
                results[house.slug] = FilterResult()
                continue

            logger.info("'%s' detected rooms: %s", house.slug, sorted(detected))
            results[house.slug] = FilterResult(
                p1={rt: rt in detected for rt in p1_types},
                p2={rt: rt in detected for rt in p2_types},
                excluded={rt: rt in detected for rt in excluded_types},
            )
        return results

    def _load_detected_types(self, slug: str) -> set[str] | None:
        """Load the set of detected room types for a house, or None if missing."""
        classifications_file = self._output_dir / slug / "room_classifications.json"
        if not classifications_file.exists():
            return None
        data = json.loads(classifications_file.read_text(encoding="utf-8"))
        return {item["room_type"] for item in data.get("classifications", [])}
