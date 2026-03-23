"""Filter pipeline runner.

Chains multiple IFilter implementations to process houses through
a configurable pipeline. Supports both sync and async execution.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from ..interfaces.filter import FilterCriteria, IFilter
from ..models.house import House

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    # Execution mode
    mode: Literal["sync", "async", "multiprocess"] = "async"

    # Parallelism settings
    max_workers: int = 4

    # Pipeline behavior
    fail_fast: bool = False  # Stop on first filter that excludes all houses
    continue_on_error: bool = True  # Continue if a single house fails

    # Logging
    log_level: int = logging.INFO


@dataclass
class PipelineResult:
    """Result of running the filter pipeline."""

    # Filtered houses
    houses: list[House]

    # Statistics
    input_count: int
    output_count: int
    filters_applied: list[str]

    # Per-filter stats
    filter_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    # Errors
    errors: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Percentage of houses that passed all filters."""
        if self.input_count == 0:
            return 0.0
        return (self.output_count / self.input_count) * 100


class FilterPipeline:
    """Chains multiple filters to process houses.

    The pipeline runs each filter in sequence, passing the results
    of one filter to the next. Supports sync, async, and multiprocess
    execution modes.

    Example:
        pipeline = FilterPipeline()
        pipeline.add_filter(text_filter)
        pipeline.add_filter(room_classifier_filter)
        pipeline.add_filter(distance_filter)

        result = await pipeline.run_async(houses, criteria)
        print(f"Filtered {result.input_count} → {result.output_count} houses")
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self.filters: list[IFilter] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._logger.setLevel(self.config.log_level)

    def add_filter(self, filter_impl: IFilter) -> "FilterPipeline":
        """Add a filter to the pipeline.

        Filters are executed in the order they are added.

        Args:
            filter_impl: Filter implementation to add.

        Returns:
            Self for method chaining.
        """
        self.filters.append(filter_impl)
        return self

    def remove_filter(self, filter_name: str) -> "FilterPipeline":
        """Remove a filter by name.

        Args:
            filter_name: Name of the filter to remove.

        Returns:
            Self for method chaining.
        """
        self.filters = [f for f in self.filters if f.name != filter_name]
        return self

    def clear_filters(self) -> "FilterPipeline":
        """Remove all filters from the pipeline.

        Returns:
            Self for method chaining.
        """
        self.filters = []
        return self

    def run(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> PipelineResult:
        """Run the pipeline synchronously.

        Args:
            houses: Houses to filter.
            criteria: Filtering criteria.

        Returns:
            Pipeline result with filtered houses and statistics.
        """
        result = PipelineResult(
            houses=list(houses),
            input_count=len(houses),
            output_count=0,
            filters_applied=[],
        )

        current_houses = list(houses)

        for filter_impl in self.filters:
            filter_name = filter_impl.name
            self._logger.info(
                f"Running filter '{filter_name}' on {len(current_houses)} houses"
            )

            before_count = len(current_houses)

            try:
                current_houses = filter_impl.filter(current_houses, criteria)
            except Exception as e:
                error_msg = f"Filter '{filter_name}' failed: {e}"
                self._logger.error(error_msg)
                result.errors.append(error_msg)
                if not self.config.continue_on_error:
                    break
                continue

            after_count = len(current_houses)
            result.filters_applied.append(filter_name)
            result.filter_stats[filter_name] = {
                "input": before_count,
                "output": after_count,
                "excluded": before_count - after_count,
            }

            self._logger.info(
                f"Filter '{filter_name}': {before_count} → {after_count} "
                f"(excluded {before_count - after_count})"
            )

            if self.config.fail_fast and after_count == 0:
                self._logger.warning(
                    f"Fail-fast: Filter '{filter_name}' excluded all houses"
                )
                break

        result.houses = current_houses
        result.output_count = len(current_houses)
        result.completed_at = datetime.now()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()

        return result

    async def run_async(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> PipelineResult:
        """Run the pipeline asynchronously.

        Uses async filter methods for I/O-bound operations.

        Args:
            houses: Houses to filter.
            criteria: Filtering criteria.

        Returns:
            Pipeline result with filtered houses and statistics.
        """
        result = PipelineResult(
            houses=list(houses),
            input_count=len(houses),
            output_count=0,
            filters_applied=[],
        )

        current_houses = list(houses)

        for filter_impl in self.filters:
            filter_name = filter_impl.name
            self._logger.info(
                f"Running async filter '{filter_name}' on {len(current_houses)} houses"
            )

            before_count = len(current_houses)

            try:
                current_houses = await filter_impl.filter_async(current_houses, criteria)
            except Exception as e:
                error_msg = f"Filter '{filter_name}' failed: {e}"
                self._logger.error(error_msg)
                result.errors.append(error_msg)
                if not self.config.continue_on_error:
                    break
                continue

            after_count = len(current_houses)
            result.filters_applied.append(filter_name)
            result.filter_stats[filter_name] = {
                "input": before_count,
                "output": after_count,
                "excluded": before_count - after_count,
            }

            self._logger.info(
                f"Filter '{filter_name}': {before_count} → {after_count} "
                f"(excluded {before_count - after_count})"
            )

            if self.config.fail_fast and after_count == 0:
                self._logger.warning(
                    f"Fail-fast: Filter '{filter_name}' excluded all houses"
                )
                break

        result.houses = current_houses
        result.output_count = len(current_houses)
        result.completed_at = datetime.now()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()

        return result

    async def run_parallel_houses(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> PipelineResult:
        """Process houses in parallel through all filters.

        Each house is processed through the full filter chain independently.
        Useful when filters are I/O-bound (API calls, storage access).

        Args:
            houses: Houses to filter.
            criteria: Filtering criteria.

        Returns:
            Pipeline result with filtered houses and statistics.
        """
        result = PipelineResult(
            houses=[],
            input_count=len(houses),
            output_count=0,
            filters_applied=[f.name for f in self.filters],
        )

        async def process_single_house(house: House) -> House | None:
            """Process a single house through all filters."""
            current = house
            for filter_impl in self.filters:
                try:
                    filtered = await filter_impl.filter_async([current], criteria)
                    if not filtered:
                        return None
                    current = filtered[0]
                except Exception as e:
                    self._logger.error(f"Error processing house {house.slug}: {e}")
                    if not self.config.continue_on_error:
                        raise
                    return None
            return current

        # Process all houses concurrently
        tasks = [process_single_house(house) for house in houses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        for r in results:
            if isinstance(r, Exception):
                result.errors.append(str(r))
            elif r is not None:
                result.houses.append(r)

        result.output_count = len(result.houses)
        result.completed_at = datetime.now()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()

        return result

    def run_multiprocess(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> PipelineResult:
        """Run the pipeline using multiprocessing for CPU-bound filters.

        Each house is processed in a separate process. Useful when filters
        are CPU-bound (image processing, heavy computation).

        Note: Filter implementations must be picklable for multiprocessing.

        Args:
            houses: Houses to filter.
            criteria: Filtering criteria.

        Returns:
            Pipeline result with filtered houses and statistics.
        """
        result = PipelineResult(
            houses=[],
            input_count=len(houses),
            output_count=0,
            filters_applied=[f.name for f in self.filters],
        )

        def process_single_house(house_data: tuple[House, FilterCriteria]) -> House | None:
            """Process a single house (runs in subprocess)."""
            house, crit = house_data
            current = house
            for filter_impl in self.filters:
                try:
                    filtered = filter_impl.filter([current], crit)
                    if not filtered:
                        return None
                    current = filtered[0]
                except Exception:
                    return None
            return current

        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            args = [(house, criteria) for house in houses]
            futures = executor.map(process_single_house, args)

            for r in futures:
                if r is not None:
                    result.houses.append(r)

        result.output_count = len(result.houses)
        result.completed_at = datetime.now()
        result.duration_seconds = (
            result.completed_at - result.started_at
        ).total_seconds()

        return result


if __name__ == "__main__":
    # CLI entry point - scaffold only
    # Will be wired up with real implementations via core.py
    import argparse

    parser = argparse.ArgumentParser(description="Run the house filter pipeline")
    parser.add_argument(
        "--mode",
        choices=["sync", "async", "multiprocess"],
        default="async",
        help="Execution mode",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Max parallel workers",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop if any filter excludes all houses",
    )

    args = parser.parse_args()

    print("Pipeline runner scaffold.")
    print(f"Mode: {args.mode}, Workers: {args.workers}, Fail-fast: {args.fail_fast}")
    print("Wire up with core.py for actual execution.")
