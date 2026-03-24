"""Filter pipeline runner.

Chains multiple IFilter implementations to process houses through
a configurable pipeline. Supports both sync and async execution.
"""

from __future__ import annotations

import logging
from typing import Any

from ..interfaces.filter import IFilter
from ..models.house import House

logger = logging.getLogger(__name__)


class FilterPipeline:
    """Chains multiple filters to process houses.

    The pipeline runs each filter in sequence, passing the results
    of one filter to the next.

    Example:
        pipeline = FilterPipeline()
        pipeline.add_filter(text_filter)
        pipeline.add_filter(room_classifier_filter)
        pipeline.add_filter(distance_filter)

        results = await pipeline.run_async(houses, criteria)
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
        """Run the pipeline synchronously."""
        current_houses = list(houses)

        for filter_impl in self.filters:
            filter_name = filter_impl.name
            before_count = len(current_houses)

            current_houses = filter_impl.filter(current_houses, criteria)

            after_count = len(current_houses)
            self._logger.info(
                f"Filter '{filter_name}': {before_count} → {after_count} "
                f"(excluded {before_count - after_count})"
            )

        return current_houses

    async def run_async(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> list[House]:
        """Run the pipeline asynchronously."""
        current_houses = list(houses)

        for filter_impl in self.filters:
            filter_name = filter_impl.name
            before_count = len(current_houses)

            current_houses = await filter_impl.filter_async(current_houses, criteria)

            after_count = len(current_houses)
            self._logger.info(
                f"Filter '{filter_name}': {before_count} → {after_count} "
                f"(excluded {before_count - after_count})"
            )

        return current_houses
