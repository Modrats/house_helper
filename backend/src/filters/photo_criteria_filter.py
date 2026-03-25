"""PhotoCriteriaFilter — IFilter wrapper around VisionPhotoChecker.

Runs the vision LLM photo criteria checker for each classified house and
converts the results into a FilterResult for the pipeline.

A house *fails* (is excluded) if any required feature is absent in ALL photos
of that room type.  P1/P2 classification is based on how many preferred
features were found.
"""

from __future__ import annotations

from typing import Any

from ..interfaces.filter import IFilter
from ..interfaces.photo_checker import IPhotoChecker
from ..models.house import FilterResult, House
from ..models.photo_criteria import RoomCriteriaResult
from ..observability import get_logger

logger = get_logger(__name__)


class PhotoCriteriaFilter(IFilter):
    """Filters houses by checking room photos against configured visual criteria.

    Delegates to a VisionPhotoChecker (IPhotoChecker) to run the LLM vision
    evaluation, then translates the results into a FilterResult so the
    FilterPipeline can include/exclude houses accordingly.

    A house is excluded when ANY required feature for a configured room type is
    absent across all photos of that room type (i.e. the feature was never
    detected).

    Args:
        photo_checker: Configured IPhotoChecker implementation.
    """

    def __init__(self, photo_checker: IPhotoChecker) -> None:
        self._checker = photo_checker

    @property
    def name(self) -> str:
        return "photo_criteria"

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        results: dict[str, FilterResult] = {}
        for house in houses:
            results[house.slug] = self._evaluate(house)
        return results

    def _evaluate(self, house: House) -> FilterResult:
        try:
            check_result = self._checker.check_house(house.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Photo criteria check failed for '%s': %s — passing through",
                house.slug,
                exc,
            )
            return FilterResult()

        if not check_result.room_results:
            logger.info("No photo criteria results for '%s' — passing through", house.slug)
            return FilterResult()

        # Aggregate pass/fail per feature across rooms.
        # Keys use "{room_type}_{feature}" so they're meaningful in filter_results.
        p1: dict[str, bool] = {}
        p2: dict[str, bool] = {}
        excluded: dict[str, bool] = {}

        # Group results per room type (a house may have multiple photos per room)
        by_room: dict[str, list[RoomCriteriaResult]] = {}
        for room_result in check_result.room_results:
            key = (
                room_result.room_type.value
                if hasattr(room_result.room_type, "value")
                else str(room_result.room_type)
            )
            by_room.setdefault(key, []).append(room_result)

        for room_type, room_photos in by_room.items():
            # Required features: a feature passes if present in ANY photo of this room
            required_names: list[str] = list(
                dict.fromkeys(f.feature_name for rr in room_photos for f in rr.required_features)
            )
            for feature in required_names:
                present_in_any = any(
                    f.present
                    for rr in room_photos
                    for f in rr.required_features
                    if f.feature_name == feature
                )
                key = f"{room_type}_{feature}"
                if not present_in_any:
                    excluded[key] = True  # dealbreaker — missing required feature
                    logger.info("'%s' missing required feature: %s", house.slug, key)
                else:
                    p1[key] = True

            # Preferred features: present in ANY photo → p1, else p2
            preferred_names: list[str] = list(
                dict.fromkeys(f.feature_name for rr in room_photos for f in rr.preferred_features)
            )
            for feature in preferred_names:
                present_in_any = any(
                    f.present
                    for rr in room_photos
                    for f in rr.preferred_features
                    if f.feature_name == feature
                )
                key = f"{room_type}_{feature}"
                if present_in_any:
                    p1[key] = True
                else:
                    p2[key] = False

        return FilterResult(p1=p1, p2=p2, excluded=excluded)
