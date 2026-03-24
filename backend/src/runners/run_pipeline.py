"""Filter pipeline runner.

Chains multiple IFilter implementations to process houses through
a configurable pipeline. Records per-filter pass/fail on each House
and advances status to FILTERED on completion.
"""

from __future__ import annotations

import logging
from typing import Any

from ..interfaces.filter import IFilter
from ..models.house import FilterResult, House, HouseStatus

logger = logging.getLogger(__name__)


class FilterPipeline:
    """Chains multiple filters to process houses.

    The pipeline runs each filter in sequence, merging per-criterion
    results into each house's FilterResult (p1/p2/excluded).
    Houses whose accumulated FilterResult.passed is False are
    dropped before the next filter runs.

    Example:
        pipeline = FilterPipeline()
        pipeline.add_filter(text_filter)
        pipeline.add_filter(distance_filter)

        results = pipeline.run(houses, criteria)
    """

    def __init__(self) -> None:
        self.filters: list[IFilter] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def add_filter(self, filter_impl: IFilter) -> "FilterPipeline":
        """Add a filter to the pipeline.

        Filters are executed in the order they are added.
        """
        self.filters.append(filter_impl)
        return self

    def run(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> list[House]:
        """Run the pipeline synchronously.

        Returns houses that passed all filters, with per-criterion
        results merged and status set to FILTERED.
        """
        current_houses = list(houses)

        for filter_impl in self.filters:
            filter_name = filter_impl.name
            before_count = len(current_houses)

            results = filter_impl.filter(current_houses, criteria)

            # Merge per-criterion results onto each house
            current_houses = [
                h.with_filter_result(results.get(h.slug, FilterResult())) for h in current_houses
            ]

            # Keep only houses whose accumulated result still passes
            current_houses = [h for h in current_houses if h.filter_results.passed]

            after_count = len(current_houses)
            self._logger.info(
                f"Filter '{filter_name}': {before_count} → {after_count} "
                f"(excluded {before_count - after_count})"
            )

        # Advance surviving houses to FILTERED
        return [h.model_copy(update={"status": HouseStatus.FILTERED}) for h in current_houses]
